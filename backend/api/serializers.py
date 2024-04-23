from drf_base64.fields import Base64ImageField

from django.contrib.auth import get_user_model, authenticate
from django.core.files.base import ContentFile

from rest_framework import serializers, validators

from recipes.models import Ingredient, IngredientRecipe, Tag, Recipe
from users.models import Subscription

from djoser.serializers import UserCreateSerializer, UserSerializer

User = get_user_model()


class TokenSerializer(serializers.Serializer):
    email = serializers.CharField(
        label='Email',
        write_only=True)
    password = serializers.CharField(
        label='Пароль',
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True)
    token = serializers.CharField(
        label='Токен',
        read_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password)
            if not user:
                raise serializers.ValidationError(
                    'Ошибка входа',
                    code='authorization')
        else:
            msg = 'Необходимо указать "адрес электронной почты" и "пароль".'
            raise serializers.ValidationError(
                msg,
                code='authorization')
        attrs['user'] = user
        return attrs


# User serializers


class UserFieldsMixin:
    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'id',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'password': {'write_only': True},
        }


class CustomUserCreateSerializer(UserFieldsMixin, UserCreateSerializer):
    email = serializers.EmailField(
        validators=[
            validators.UniqueValidator(
                User.objects.all()
            )
        ]
    )


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserFieldsMixin.Meta):
        fields = UserFieldsMixin.Meta.fields + ('is_subscribed',)

    def get_is_subscribed(self, obj):
        return Subscription.objects.filter(user=obj).exists()


class UserSerializerWithRecipesList(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = (CustomUserSerializer.Meta.fields
                  + ('recipes', 'recipes_count'))

    def get_recipes_count(self, user):
        return Recipe.objects.filter(author=user).count()

    def get_recipes(self, user):
        limit = self._get_limit_recipe()
        recipes = user.recipe.all()
        if limit:
            recipes = recipes[:limit]
        serializer = RecipeListForUserSerializer(recipes)
        return serializer.data

    def _get_limit_recipe(self):
        recipes_limit = self.context.get('recipes_limit', False)
        return int(recipes_limit)


class SubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializerWithRecipesList()

    class Meta:
        model = Subscription
        fields = ('user',)

    def to_representation(self, instance):
        return super().to_representation(instance).get('user')

# Recipe Serializers


class TagSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')
        read_only_fields = ('color', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = '__all__'
        read_only_fields = ('measurement_unit', 'name',)


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(source='id_ingredient')
    measurement_unit = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all())
    ingredients = serializers.ListField(
        write_only=True,
        required=True,
        allow_empty=False,)
    author = CustomUserSerializer(read_only=True)
    cooking_time = serializers.IntegerField(allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'ingredients', 'tags',
                  'image', 'name', 'text',
                  'cooking_time', 'author',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self._add_ingredientrecipe(ingredients_data, recipe)
        self._add_tagrecipe(tags_data, recipe)
        return recipe

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = self.context['request'].user
        representation['ingredients'] = [
            IngredientRecipeSerializer(ingredient).data
            for ingredient in IngredientRecipe.objects.filter(recipe=instance)
        ]
        representation['is_favorited'] = user in instance.is_favorited.all()
        representation['is_in_shopping_cart'] = user in instance.is_in_shopping_cart.all()
        representation['image'] = instance.image.url
        return representation

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)
        if ingredients_data is not None:
            self._add_ingredientrecipe(ingredients_data, instance)
        if tags_data is not None:
            self._add_tagrecipe(tags_data, instance)
        return super().update(instance, validated_data)

    def validate_ingredients(self, ingredients):
        ids = set(i['id'] for i in ingredients)
        if len(ingredients) != len(ids):
            raise serializers.ValidationError('Ингредиент не должен повторяться')
        for ingredient_data in ingredients:
            if not Ingredient.objects.filter(pk=ingredient_data['id']).exists():
                raise serializers.ValidationError('Такого ингредиента нет')
            if not ingredient_data.get('количество'):
                raise serializers.ValidationError('Количество отрицательно')
        return ingredients

    def validate_tags(self, tags):
        ids = set(i['id'] for i in tags)
        if len(tags) != len(ids):
            raise serializers.ValidationError('Ингредиент не должен повторяться')
        for tag in tags:
            if not Tag.objects.filter(pk=tag['id']).exists():
                raise serializers.ValidationError('Такого ингредиента нет')
        return tags

    def validate_cooking_time(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Время отрицательно')
        return attrs

    def _add_ingredientrecipe(self, ingredients, instance):
        if not ingredients:
            raise serializers.ValidationError('Добавьте ингредиенты')
        IngredientRecipe.objects.filter(recipe=instance).delete()
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                ingredient=Ingredient.objects.get(pk=ingredient['id']),
                recipe=instance,
                amount=ingredient.get('сумма')
            )
            for ingredient in ingredients
        ])

    def _add_tagrecipe(self, tags, instance):
        if not tags:
            raise serializers.ValidationError('Добавьте тег')
        instance.tags.clear()
        instance.tags.add(*Tag.objects.filter(pk__in=[tag['id'] for tag in tags]))


class RecipeListForUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image')

    def get_name(self, obj):
        return obj.name if obj else None


