from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe,
                            ShoppingCart, Tag)
from rest_framework import (
    exceptions,
    mixins,
    permissions,
    status,
    viewsets,
    serializers
)
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from users.models import Subscription

from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeCreateSerializer,
                          RecipeSubscribeSerializer, SubscriptionSerializer,
                          TagSerializer)
from .services import create_pdf

User = get_user_model()


class UserActionViewSet(UserViewSet):
    @action(["get", "put", "patch", "delete"],
            detail=False,
            permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(['POST'],
            detail=True, serializer_class=SubscriptionSerializer)
    def subscribe(self, request, *args, **kwargs):
        user_obj = self.get_object()

        if request.method == 'POST':
            if request.user == user_obj:
                return Response(
                    "Нельзя подписываться на самого себя",
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription, created = Subscription.objects.get_or_create(
                user=user_obj,
                subscriber=request.user
            )

            if not created:
                return Response(
                    'Вы уже подписаны!',
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = SubscriptionSerializer(
                subscription,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, *args, **kwargs):
        user_obj = self.get_object()
        del_count, _ = Subscription.objects.filter(
            user=user_obj,
            subscriber=request.user
        ).delete()
        if not del_count:
            raise serializers.ValidationError(
                'Вы не были подписаны на данного автора.'
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

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


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly, ]
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
        _, deleted_count = obj_class.objects.filter(
            user=user,
            recipe=recipe
        ).delete()
        if deleted_count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                "Рецепта нет в избранных",
                status=status.HTTP_400_BAD_REQUEST
            )

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
        file = create_pdf(request.user)
        return file

    @action(methods=['POST'],
            permission_classes=(permissions.IsAuthenticated,),
            detail=True)
    def favorite(self, request, pk=None):
        return self.create_obj(request, Favorite)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
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

    def destroy(self, request, *args, **kwargs):
        user_obj = self.get_object()
        del_count, _ = Subscription.objects.filter(
            user=user_obj,
            subscriber=request.user
        ).delete()
        if not del_count:
            raise serializers.ValidationError(
                'Вы не были подписаны на данного автора.'
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
