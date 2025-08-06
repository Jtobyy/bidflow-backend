from django.contrib import admin
from .models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'company', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('avatar', 'company')}),
    )
