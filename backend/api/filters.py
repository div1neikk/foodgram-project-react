from django_filters import rest_framework as filters

from recipes.models import Ingredient, Tag


class RecipeFilter(filters.FilterSet):
    author = filters.NumberFilter(field_name='author__id')
    is_favorited = filters.BooleanFilter(
        method='get_is_favorited',
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='get_is_in_shopping_cart',
    )
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tag.objects.all(),
        to_field_name='slug',
        method='filter_tags'
    )

    def get_is_favorited(self, queryset, filter_name, filter_value):
        if filter_value:
            return queryset.filter(is_favorited=self.request.user.id)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(is_in_shopping_cart=user)
        return queryset

    def filter_tags(self, queryset, name, value):
        return queryset.filter(tags__in=value).distinct()


class IngredientFilter(filters.FilterSet):

    name = filters.CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
