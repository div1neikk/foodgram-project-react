import django_filters

from recipes.models import Ingredient, Recipe


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(field_name='author__id')
    tags = django_filters.CharFilter(
        method='filter_tags')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_user_in_queryset')
    is_favorited = django_filters.NumberFilter(
        method='filter_user_in_queryset')

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_in_shopping_cart', 'is_favorited',)

    def filter_user_in_queryset(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            data = {name: user}
            queryset = queryset.filter(**data)
        return queryset

    def filter_tags(self, queryset, name, value):
        tags = self.request.query_params.getlist('tags')
        queryset = queryset.filter(tags__slug__in=tags).distinct()
        return queryset


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name', lookup_expr='icontains'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)
