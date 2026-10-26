from django.contrib import admin
from .models import Category, Case, Attachment, AuditLog


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("case_number", "title", "case_type", "priority", "status", "created_at")
    list_filter = ("status", "priority", "case_type", "category")


admin.site.register([Category, Attachment, AuditLog])