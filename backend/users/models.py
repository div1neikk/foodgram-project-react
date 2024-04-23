from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True
    )
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='Группы',
        blank=True,
        related_name='custom_users'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='Разрешения пользователя',
        blank=True,
        related_name='custom_users_permissions'
    )
    first_name = models.CharField(
        'Имя',
        max_length=150)
    last_name = models.CharField(
        'Фамилия',
        max_length=150)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self):
        return self.email


class Subscription(models.Model):
    subscriber = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscriber'
    )
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='user'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        default_related_name = 'ingredient'
        constraints = (
            models.UniqueConstraint(
                fields=('subscriber', 'user'),
                name='user_following_unique'
            ),
        )

    def __str__(self):
        return f'{self.subscriber} is subscribed to {self.user}'

    def clean_recipients(self):
        if self.user == self.subscriber:
            raise ValidationError(
                'Вы не можете подписаться на самого себя'
            )
