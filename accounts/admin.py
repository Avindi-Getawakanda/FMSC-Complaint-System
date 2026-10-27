from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "department")
    list_select_related = ("user",)