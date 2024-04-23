from django.contrib import admin
from django.contrib.auth import get_user_model, models
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

from .models import Subscription

User = get_user_model()

admin.site.unregister(models.Group)


class CustomUserAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'email',
        'first_name', 'last_name', 'date_joined',)
    search_fields = ('email', 'username', 'first_name', 'last_name')
    list_filter = ('date_joined', 'email', 'first_name')
    empty_value_display = '-пусто-'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.unregister(User)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscriber')
    list_filter = ('user', 'subscriber')
