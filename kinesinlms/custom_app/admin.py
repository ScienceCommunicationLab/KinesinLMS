# Register your models here.

from django.contrib import admin

from kinesinlms.custom_app.models import (
    AppItem,
    CustomApp,
    CustomAppStudentSettings,
    PeerComment,
)


class AppItemsInline(admin.TabularInline):
    model = AppItem
    extra = 0
    show_change_link = True


@admin.register(CustomApp)
class CustomAppAdmin(admin.ModelAdmin):
    model = CustomApp
    list_display = ("id", "tab_label", "display_name", "slug", "course", "description")
    list_display_links = ("id", "tab_label")
    inlines = [AppItemsInline]


@admin.register(CustomAppStudentSettings)
class CustomAppStudentSettingsAdmin(admin.ModelAdmin):
    model = CustomAppStudentSettings
    list_display = (
        "id",
        "student",
        "allow_public_view",
        "allow_user_view",
        "allow_user_comments",
        "allow_classmate_view",
        "allow_classmate_comments",
    )
    list_display_links = ("id", "student")


@admin.register(AppItem)
class AppItemAdmin(admin.ModelAdmin):
    model = AppItem
    list_display = (
        "id",
        "type",
        "custom_app",
        "assessment",
        "order",
        "html_content",
        "json_content",
    )
    list_display_links = ("id",)


@admin.register(PeerComment)
class PeerCommentAdmin(admin.ModelAdmin):
    model = PeerComment
    list_display = (
        "id",
        "custom_app",
        "student_owner",
        "author",
        "html_content",
        "json_content",
    )
    list_display_links = ("id",)
