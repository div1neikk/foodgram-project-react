from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


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

    def clean(self):
        if self.user == self.subscriber:
            raise ValidationError(
                'Вы не можете подписаться на самого себя'
            )
