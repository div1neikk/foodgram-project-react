from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    email = models.EmailField(unique=True, verbose_name='Почта')

    def __str__(self):
        return self.username


class Subscription(models.Model):
    subscriber = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True,
        related_name='subscriber',
    )
    user = models.ForeignKey(
        User,
        null=True,
        on_delete=models.CASCADE,
        related_name='user',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('subscriber', 'user'),
                name='user_following_unique'
            ),
        )

    def __str__(self):
        return f'{self.subscriber} is subscribed to {self.user}'
