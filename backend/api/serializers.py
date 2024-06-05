from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import (
    UserCreateSerializer as
    DjoserUserCreateSerializer
)
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_base64.fields import Base64ImageField
from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from rest_framework import serializers
from users.models import Subscription

User = get_user_model()


class UserCreateSerializer(DjoserUserCreateSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'password': {'write_only': True},
        }


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField(
        required=False,
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'id',
            'first_name',
            'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return (
                Subscription.objects.filter(user=obj).exists()
            )
        return False


class RecipeSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source='subscriber.username',
        read_only=True
    )
    email = serializers.EmailField(
        source='subscriber.email',
        read_only=True
    )
    first_name = serializers.CharField(
        source='subscriber.first_name',
        read_only=True
    )
    last_name = serializers.CharField(
        source='subscriber.last_name',
        read_only=True
    )
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        recipes = Recipe.objects.filter(author=obj.user)
        return RecipeSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.user).count()

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return Subscription.objects.filter(
            subscriber=user
        ).exists()

    def validate(self, data):
        user = self.context['request'].user
        user_obj = data['user']
        if user == user_obj:
            raise serializers.ValidationError(
                "Нельзя подписываться на самого себя"
            )
        if Subscription.objects.filter(
                user=user_obj, subscriber=user
        ).exists():
            raise serializers.ValidationError('Вы уже подписаны!')
        return data


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug'
        )
        read_only_fields = (
            'id',
            'color',
            'name',
            'slug'
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(source='id_ingredient')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'amount',
            'measurement_unit'
        )


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(required=False, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField()
    ingredients = RecipeIngredientSerializer(
        many=True, read_only=True
    )
    is_favorited = serializers.BooleanField(
        source='is_favorited',
        read_only=True,
        default=False
    )
    is_in_shopping_cart = serializers.BooleanField(
        source='is_in_shopping_cart',
        read_only=True,
        default=False
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_ingredients(self, obj):
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return [
            {
                'id': recipe_ingredient.ingredient.id,
                'name': recipe_ingredient.ingredient.name,
                'amount': recipe_ingredient.amount,
                'measurement_unit':
                    recipe_ingredient.ingredient.measurement_unit
            }
            for recipe_ingredient in recipe_ingredients
        ]


class RecipeCreateSerializer(serializers.ModelSerializer):
    author = UserSerializer(required=False, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField()
    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=True,
        allow_empty=False,
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    @transaction.atomic
    def create_bulk_ing_tag(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    amount=ing['amount'],
                    ingredient=Ingredient.objects.get(id=ing['id']),
                ) for ing in ingredients
            ]
        )

    def get_object_or_raise_404(self, pk):
        try:
            return Recipe.objects.get(pk=pk)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError(
                detail='Рецепта не существует'
            )

    def validate(self, data):

        ingredients = data.get('ingredients', [])
        tags = data.get('tags', [])
        self.validate_tags(tags)
        self.validate_ingredients(ingredients)
        self.validate_cooking_time(data.get('cooking_time', 1))
        return data

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError('Добавьте тег')
        if len(tags) == 0:
            raise serializers.ValidationError(
                'Поле "tags" не должно быть пустым.'
            )
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError('Теги не должны повторяться.')

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError('Добавьте ингридиент')

        ingredient_ids = [ingredient.get('id') for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        existing_ids = set(Ingredient.objects.values_list('id', flat=True))

        for ingredient_data in ingredients:
            self.validate_ingredient(ingredient_data, existing_ids)

    def validate_ingredient(self, ingredient_data, existing_ids):
        ing_id = ingredient_data.get('id')
        if ing_id not in existing_ids:
            raise serializers.ValidationError(
                f'Ингредиент с id {ing_id} не существует.'
            )

        amount = ingredient_data.get('amount')

        if amount is None:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть указано.'
            )

        try:
            amount = int(amount)
        except ValueError:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть числом.'
            )

        if amount <= 0:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше 0.'
            )

    def validate_cooking_time(self, cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                'Время готовки должно быть больше 1 минуты.'
            )

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self.create_bulk_ing_tag(recipe, ingredients_data)
        recipe.tags.set(tags_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        if tags_data:
            instance.tags.set(tags_data)
        if ingredients_data:
            RecipeIngredient.objects.filter(recipe=instance).delete()
            self.create_bulk_ing_tag(instance, ingredients_data)
        instance.save()
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(instance, context={
            'request': self.context.get('request')
        }).data
