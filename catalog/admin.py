from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "recommended_age",
        "is_available",
        "created_at",
    )
    list_filter = ("category", "is_available")
    search_fields = ("name", "description", "slug")
    ordering = ("name",)
    list_select_related = ("category",)
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "slug", "description", "category")
        }),
        ("Продажа", {"fields": ("price", "recommended_age", "is_available")}),
        ("Изображение", {"fields": ("image",)}),
    )
