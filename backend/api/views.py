from django.db.models import Sum
from django.http import FileResponse
from django_filters import rest_framework as filters
from rest_framework import (
    exceptions,
    mixins,
    permissions,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitPageNumberPagination
from .permissions import AuthorAndAdminOnly
from .serializers import (
    IngredientSerializer,
    RecipeListForUserSerializer,
    RecipeSerializer,
    TagSerializer,
    SubscriptionSerializer,
    UserSerializerWithRecipesList,
)
from .services import create_pdf
from recipes.models import (
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag,
    UsersRecipesFavorite,
)
from users.models import Subscription

from djoser.views import UserViewSet
from rest_framework.permissions import IsAuthenticated


def _get_obj_or_400(klass, **kwargs):
    if hasattr(klass, "_default_manager"):
        queryset = klass._default_manager.all()
    try:
        return queryset.get(**kwargs)
    except Exception:
        raise exceptions.ValidationError(detail=f'{klass.__name__} not exist')


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (AuthorAndAdminOnly,)
    pagination_class = LimitPageNumberPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(["post", "delete"],
            permission_classes=(permissions.IsAuthenticated,),
            detail=True)
    def shopping_cart(self, request, *args, **kwargs):
        return self.__base_action_method(
            ShoppingCart, request, *args, **kwargs
        )

    @action(["get"],
            permission_classes=(permissions.IsAuthenticated,),
            detail=False)
    def download_shopping_cart(self, request, *args, **kwargs):
        recipes_in_shopping_cart = IngredientRecipe.objects.filter(
            recipe__is_in_shopping_cart=request.user
        ).values('ingredient__name',
                 'ingredient__measurement_unit',
                 ).annotate(amount=Sum('amount')).order_by('ingredient__name')
        file = create_pdf(recipes_in_shopping_cart)
        return FileResponse(
            file,
            filename='shopping_cart.pdf',
            status=status.HTTP_200_OK,
            as_attachment=True, )

    @action(['post', 'delete'],
            permission_classes=(permissions.IsAuthenticated,),
            detail=True)
    def favorite(self, request, *args, **kwargs):
        return self.__base_action_method(
            UsersRecipesFavorite, request, *args, **kwargs)

    def _get_recipe_or_400(self):
        try:
            recipe = self.get_object()
            return recipe
        except Exception:
            raise exceptions.ValidationError(detail='Recipe not exist')

    def __base_action_method(
            self, klass, request, *args, **kwargs
    ) -> Response:
        """Return Response depending on the state of the objects."""
        method = request.method
        user = request.user
        if method == 'POST':
            recipe = self._get_recipe_or_400()
            serializer = RecipeListForUserSerializer(recipe)
            _, created = klass.objects.get_or_create(user=user, recipe=recipe)
            if created:
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                'Recipe already in list',
                status=status.HTTP_400_BAD_REQUEST
            )
        if method == 'DELETE':
            recipe = self.get_object()
            favorite = _get_obj_or_400(klass, user=user, recipe=recipe)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.order_by('name')
    serializer_class = IngredientSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(mixins.RetrieveModelMixin,
                 mixins.ListModelMixin,
                 viewsets.GenericViewSet):
    queryset = Tag.objects.order_by('id')
    serializer_class = TagSerializer
    pagination_class = None


class SubscriptionViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Subscription.objects.filter(subscriber=user)
        limit = self.request.query_params.get('limit', False)
        if limit:
            queryset = queryset[:int(limit)]
        return queryset

    def get_serializer_context(self):
        context = self.request.query_params
        return context


class UserViewSetWithActions(UserViewSet):

    @action(["get", "put", "patch", "delete"],
            detail=False,
            permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(["post", "delete"], detail=True)
    def subscribe(self, request, *args, **kwargs):
        user = self.get_object()
        subscriber = request.user
        sub_exist = Subscription.objects.filter(
            user=user, subscriber=subscriber
        ).exists()
        if user == subscriber:
            return Response('Вы не можете подписаться на самого себя',
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'POST':
            if sub_exist:
                return Response('Вы уже подписаны',
                                status=status.HTTP_400_BAD_REQUEST)
            Subscription.objects.create(user=user, subscriber=subscriber)
            serializer = UserSerializerWithRecipesList(
                user, context=request.query_params
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            if not sub_exist:
                return Response('Вы не подписаны',
                                status=status.HTTP_400_BAD_REQUEST)
            Subscription.objects.get(user=user, subscriber=subscriber).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
