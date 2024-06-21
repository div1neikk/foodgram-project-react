from colorfield.fields import ColorField
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Exists, OuterRef
from django.core.validators import MinValueValidator

User = get_user_model()


class RecipeQuerySet(models.QuerySet):

    def with_user_annotations(self, user):
        if user.is_authenticated:
            return self.annotate(
                is_favorited_by_user=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart_by_user=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            ).prefetch_related('ingredients')
        return self


class RecipeManager(models.Manager):

    def get_queryset(self):
        return RecipeQuerySet(self.model, using=self._db)

    def with_user_annotations(self, user):
        return self.get_queryset().with_user_annotations(user)


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128, unique=True,
        verbose_name='название'
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'ингредиенты'
        constraints = (
            models.UniqueConstraint(fields=('name', 'measurement_unit'),
                                    name='ingredient_unique'),
        )

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=128, unique=True,
        verbose_name='тэг'
    )
    color = ColorField(default='#FF0000')
    slug = models.SlugField(
        max_length=200, verbose_name='Слаг',
        unique=True
    )

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'тэги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    name = models.CharField(
        max_length=128, unique=True,
        verbose_name='название'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authored_recipes',
        verbose_name='Автор',
    )
    image = models.ImageField(verbose_name='Картинка')
    text = models.TextField(verbose_name='Описание')
    tags = models.ManyToManyField(Tag, verbose_name='тэг')
    ingredients = models.ManyToManyField(
        Ingredient, through='RecipeIngredient',
        verbose_name='Ингредиенты',
        related_name='recipes'
    )
    cooking_time = models.PositiveSmallIntegerField(
        blank=False,
        validators=[
            MinValueValidator(1, message='Время приготовления меньше 1 минуты')
        ],
        verbose_name='Время приготовления'
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
        null=True
    )
    is_favorited = models.ManyToManyField(
        User,
        through='Favorite',
        verbose_name='Избранный рецепт',
        related_name='favorite_recipes',
    )
    is_in_shopping_cart = models.ManyToManyField(
        User,
        through='ShoppingCart',
        verbose_name='В корзине',
        related_name='shopping_cart_recipes'
    )
    objects = RecipeManager()

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='ingredient_recipes'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1, 'Значение меньше 1')],
        default=1,
        verbose_name='Количество'
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Ингредиенты для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'
        constraints = (
            models.UniqueConstraint(fields=('ingredient', 'recipe'),
                                    name='unique_ingredient_recipe'),
        )

    def __str__(self) -> str:
        return f'{self.recipe} {self.ingredient}'


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_favorite',
        verbose_name='Рецепт',
    )

    class Meta:
        ordering = ('user',)
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='user_recipe_favorite_unique'),
        )

    def __str__(self) -> str:
        return f'{self.user} {self.favorited}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='shopping_cart'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'
        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='user_recipe_shopping_cart_unique'),
        )

    def __str__(self) -> str:
        return f'{self.user} {self.recipe}'
