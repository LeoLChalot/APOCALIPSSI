"""Admin Django.

User utilise l'admin par défaut. On enregistre en revanche `DataRequest` (le
registre d'audit RGPD) en LECTURE SEULE : ces lignes sont des preuves de
conformité, elles ne doivent pas être modifiables à la main depuis l'admin.
"""

from django.contrib import admin

from .models import DataRequest


@admin.register(DataRequest)
class DataRequestAdmin(admin.ModelAdmin):
    list_display = ("request_type", "user_email", "status", "requested_at", "answered_at")
    list_filter = ("request_type", "status", "requested_at")
    search_fields = ("user_email",)
    date_hierarchy = "requested_at"
    ordering = ("-requested_at",)
    readonly_fields = (
        "user",
        "user_email",
        "request_type",
        "status",
        "requested_at",
        "answered_at",
        "export_hash",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
