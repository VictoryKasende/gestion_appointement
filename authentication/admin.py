from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from authentication.models import Utilisateur


class UtilisateurAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'telephone', 'role', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'role')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {'fields': ('matricule', 'first_name', 'last_name', 'email', 'telephone', 'genre', 'profile_photo')}),
        ('Rôle et statut', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'telephone', 'genre', 'role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    ordering = ('username',)


admin.site.register(Utilisateur, UtilisateurAdmin)
