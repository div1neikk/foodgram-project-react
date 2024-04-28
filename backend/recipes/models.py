from colorfield.fields import ColorField
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class NameFieldBaseModel(models.Model):
    name = models.CharField(
        'Название',
        max_length=128,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Ingredient(NameFieldBaseModel):
    measurement_unit = models.CharField(
        'Единица измерения', max_length=200)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'ингредиенты'
        default_related_name = 'ingredient'
        constraints = (
            models.UniqueConstraint(fields=('name', 'measurement_unit'),
                                    name='ingredient_unique'),
        )


class Tag(NameFieldBaseModel):
    slug = models.CharField(max_length=200, unique=True)
    color = ColorField(default='#FF0000')

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'тэги'
        default_related_name = 'tag'


class Recipe(NameFieldBaseModel):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    image = models.ImageField(
        upload_to='images/',
        null=False,
        blank=False,
        verbose_name='Изображение',
    )
    text = models.TextField('Описание',)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
    )
    cooking_time = models.PositiveSmallIntegerField(
        blank=False,
        verbose_name='Время приготовления',
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True
    )
    is_favorited = models.ManyToManyField(
        User,
        through='UsersRecipesFavorite',
        related_name='favorite_recipes',
        verbose_name='Кому понравился рецепт'
    )

    is_in_shopping_cart = models.ManyToManyField(
        User,
        through='ShoppingCart',
        related_name='buy_it',
        verbose_name='Кто добавил в список покупок',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipe'
        ordering = ('-pub_date',)


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField()
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(fields=('ingredient', 'recipe'),
                                    name='unique_ingredient_recipe'),
        )
    verbose_name = 'Ингредиент'
    verbose_name_plural = 'ингредиенты'
    default_related_name = 'ingredient_recipe'


class AbstractUserRecipeModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True


class ShoppingCart(AbstractUserRecipeModel):

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = verbose_name
        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='user_recipe_shopping_cart_unique'),
        )


class UsersRecipesFavorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        null=True,
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Покупка')

    class Meta:
        verbose_name = 'Любимый рецепт пользователя'
        verbose_name_plural = 'любимые рецепты пользователя'
        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='user_recipe_favorite_unique'),
        )
