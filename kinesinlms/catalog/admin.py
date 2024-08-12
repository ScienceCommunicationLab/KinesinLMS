# Register your models here.


from django.contrib import admin

from kinesinlms.catalog.models import CourseCatalogDescription


@admin.register(CourseCatalogDescription)
class CourseCatalogDescriptionAdmin(admin.ModelAdmin):
    model = CourseCatalogDescription

    list_display = (
        "id",
        "token",
        "title",
        "blurb",
        "thumbnail",
        "visible",
        "hex_theme_color",
        "effort",
        "course",
    )
    list_display_links = ("id", "title")
