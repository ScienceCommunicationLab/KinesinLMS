from django.contrib import admin

# Register your models here.
from kinesinlms.composer.models import CourseImportTaskResult, EditStatus


@admin.register(EditStatus)
class EditStatusAdmin(admin.ModelAdmin):
    model = EditStatus
    list_display = ("id", "course", "mode")


@admin.register(CourseImportTaskResult)
class CourseImportTaskResultAdmin(admin.ModelAdmin):
    model = CourseImportTaskResult
    list_display = (
        "id",
        "generation_status",
        "display_name",
        "course_slug",
        "course_run",
        "create_forum_items",
        "error_message",
        "import_file",
    )
    list_filter = ("generation_status",)
