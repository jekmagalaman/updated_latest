from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Unit, Department


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "role",
        "unit",
        "department",
        "account_status",
        "is_staff",
    )
    list_filter = ("role", "account_status", "unit", "department", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)

    # ✅ Show first_name and last_name in the form view
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Role & Assignment", {"fields": ("role", "account_status", "unit", "department")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # ✅ Also include them when adding a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name",
                "last_name",
                "email",
                "password1",
                "password2",
                "role",
                "account_status",
                "unit",
                "department",
                "is_staff",
                "is_superuser",
            ),
        }),
    )


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
