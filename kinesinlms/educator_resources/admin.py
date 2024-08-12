from django.contrib import admin

from kinesinlms.educator_resources.models import EducatorSurvey, EducatorResource


@admin.register(EducatorResource)
class EducatorResourcesAdmin(admin.ModelAdmin):
    model = EducatorResource
    list_display = (
        "id",
        "type",
        "name",
        "course",
        "overview",
        "enabled",
        "file",
        "url"
    )


@admin.register(EducatorSurvey)
class EducatorSurveyAdmin(admin.ModelAdmin):
    model = EducatorSurvey
    list_display = ("id", "email", "institution", "plan_to_use", "evaluating")
