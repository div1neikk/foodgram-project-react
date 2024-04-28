from django.contrib import admin
from django.contrib.auth import get_user_model, models
from django.contrib.auth.admin import UserAdmin

from .models import Subscription

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_filter = ('username', 'email',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscriber')
    list_filter = ('user', 'subscriber')


admin.site.unregister(models.Group)
