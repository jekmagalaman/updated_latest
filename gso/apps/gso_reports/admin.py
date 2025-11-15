from django.contrib import admin
from .models import WorkAccomplishmentReport, SuccessIndicator

@admin.register(SuccessIndicator)
class SuccessIndicatorAdmin(admin.ModelAdmin):
    list_display = ("code", "unit", "description", "is_active")
    list_filter = ("unit", "is_active")
    search_fields = ("code", "description", "activity_name__name")


@admin.register(WorkAccomplishmentReport)
class WorkAccomplishmentReportAdmin(admin.ModelAdmin):
    list_display = ("activity_name", "unit", "date_started", "status", "total_cost")
    list_filter = ("unit", "status", "date_started")
    search_fields = ("activity_name", "description")
