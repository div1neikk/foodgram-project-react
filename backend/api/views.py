from django.http import FileResponse
from rest_framework import viewsets, mixins, status, permissions
from rest_framework.permissions import (IsAuthenticatedOrReadOnly,
                                        IsAuthenticated)
from django_filters import rest_framework as filters
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef
from djoser.views import UserViewSet
from recipes.models import (Recipe, Ingredient, Tag,
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

    @action(['POST', 'DELETE'],
            detail=True, serializer_class=SubscriptionSerializer)
    def subscribe(self, request, *args, **kwargs):
        user_obj = self.get_object()
        if request.user == user_obj:
            return Response("Нельзя подписываться на самого себя",
                            status=status.HTTP_400_BAD_REQUEST)

        subscription, created = Subscription.objects.get_or_create(
            user=user_obj,
            subscriber=request.user
        )

        if not created:
            return Response('Вы уже подписаны!',
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = SubscriptionSerializer(
            subscription, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request):
        user_obj = self.get_object()
        try:
            subscription = Subscription.objects.get(
                user=user_obj,
                subscriber=request.user
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
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

    def get_queryset(self):
        user = self.request.user
        queryset = Recipe.objects.all()

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            )
        else:
            queryset = queryset.annotate(
                is_favorited=Exists(Favorite.objects.none()),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.none()
                )
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_obj_or_404(self, pk):
        serializer = self.get_serializer()
        return serializer.get_object_or_raise_404(pk)

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
        user = get_object_or_404(User, username=request.user.username)
        pdf_buffer = create_pdf(user)
        return FileResponse(pdf_buffer, as_attachment=True,
                            filename='shopping_cart.pdf')

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
        subscriber = self.request.user
        return Subscription.objects.filter(subscriber=subscriber)
