from django.db.models import Sum
from django.http import FileResponse
from rest_framework import viewsets, mixins, status, permissions, exceptions
from rest_framework.permissions import (IsAuthenticatedOrReadOnly,
                                        IsAuthenticated)
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from djoser.views import UserViewSet
from recipes.models import (Recipe, Ingredient, Tag, RecipeIngredient,
                            Favorite, ShoppingCart)
from rest_framework.decorators import action
from rest_framework.response import Response


from .serializers import (
    IngredientSerializer,
    TagSerializer,
    RecipeCreateSerializer,
    SubscriptionSerializer,
    RecipeSubscribeSerializer
)

from users.models import Subscription

from .permissions import AuthorAndAdminOnly

from .pagination import LimitPageNumberPagination
from .filters import IngredientFilter, RecipeFilter
from .services import create_pdf


from django.contrib.auth import get_user_model


User = get_user_model()


class UserValidateViewSet(UserViewSet):
    @action(["get", "put", "patch", "delete"],
            detail=False,
            permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(['POST', 'DELETE'], detail=True)
    def subscribe(self, request, *args, **kwargs):
        user_obj = self.get_object()
        if request.method == 'POST':
            if request.user == user_obj:
                return Response("Нельзя подписываться на самого себя",
                                status=status.HTTP_400_BAD_REQUEST)

            sub_exist = Subscription.objects.filter(
                user=user_obj, subscriber=request.user
            ).exists()

            if sub_exist:
                return Response('Вы уже подписаны!',
                                status=status.HTTP_400_BAD_REQUEST)

            subscription = Subscription.objects.create(
                user=user_obj,
                subscriber=request.user
            )
            serializer = SubscriptionSerializer(
                subscription, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            try:
                subscription = Subscription.objects.get(
                    user=user_obj,
                    subscriber=request.user
                )
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ObjectDoesNotExist:
                return Response("Вы не подписаны на этого пользователя",
                                status=status.HTTP_400_BAD_REQUEST)

    @action(['get'], detail=False, permission_classes=(
            IsAuthenticatedOrReadOnly,)
            )
    def subscriptions(self, request, *args, **kwargs):
        user = request.user
        subscriptions = Subscription.objects.filter(subscriber=user)

        paginator = LimitPageNumberPagination()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request
        )

        if paginated_subscriptions is not None:
            serializer = SubscriptionSerializer(
                paginated_subscriptions,
                many=True,
                context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            subscriptions,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter
    search_fields = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [AuthorAndAdminOnly, ]
    serializer_class = RecipeCreateSerializer
    pagination_class = LimitPageNumberPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_obj_or_404(self):
        try:
            recipe = self.get_object()
            return recipe
        except Exception:
            raise exceptions.ValidationError(detail='Рецепта нет')

    def create_obj(self, request, obj_class):
        recipe = self.get_obj_or_404()
        obj, created = obj_class.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        if created:
            serializer = RecipeSubscribeSerializer(recipe)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            'Ошибка создания',
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete_obj(self, request, obj_class):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=self.kwargs.get('pk'))
        try:
            obj_instance = obj_class.objects.get(user=user, recipe=recipe)
            obj_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except obj_class.DoesNotExist:
            return Response("Рецепта нет в избранных",
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            detail=True)
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.create_obj(request, ShoppingCart)
        elif request.method == 'DELETE':
            return self.delete_obj(request, ShoppingCart)

    @action(["get"],
            permission_classes=(permissions.IsAuthenticated,),
            detail=False)
    def download_shopping_cart(self, request, *args, **kwargs):
        recipes_in_shopping_cart = RecipeIngredient.objects.filter(
            recipe__shoppingcart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(amount=Sum('amount')).order_by('ingredient__name')
        file = create_pdf(recipes_in_shopping_cart)
        return FileResponse(
            file,
            filename='shopping_cart.pdf',
            status=status.HTTP_200_OK,
            as_attachment=True,
        )

    @action(methods=['POST', 'DELETE'],
            permission_classes=(permissions.IsAuthenticated,),
            detail=True)
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.create_obj(request, Favorite)
        elif request.method == 'DELETE':
            return self.delete_obj(request, Favorite)


class SubscriptionViewSet(mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        return Subscription.objects.filter(subscriber=user)
