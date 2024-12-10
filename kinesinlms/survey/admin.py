from django.contrib import admin

from kinesinlms.survey.models import Survey, SurveyCompletion, SurveyEmail, SurveyProvider


@admin.register(SurveyProvider)
class SurveyProviderAdmin(admin.ModelAdmin):
    model = SurveyProvider
    list_display = (
        "id",
        "name",
        "type",
        "slug",
        "datacenter_id",
        "api_key",
        "callback_secret",
    )


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    model = Survey
    list_display = (
        "id",
        "slug",
        "type",
        "name",
        "survey_id",
        "course_slug",
        "course_run",
        "send_reminder_email",
        "days_delay",
        "provider",
        "url",
    )

    def course_slug(self, obj):
        if obj.course:
            return obj.course.slug
        return ""

    def course_run(self, obj):
        if obj.course:
            return obj.course.run
        return ""

    course_slug.short_description = "Course Slug"
    course_slug.admin_order_field = "course__slug"

    course_run.short_description = "Course Run"
    course_run.admin_order_field = "course__run"


@admin.register(SurveyEmail)
class SurveyEmailAdmin(admin.ModelAdmin):
    model = SurveyEmail
    search_fields = ("user__username", "user__anon_username", "survey__type")
    list_display = ("user", "anon_username", "survey", "scheduled_date", "status")

    def anon_username(self, obj):
        return obj.user.anon_username


@admin.register(SurveyCompletion)
class SurveyCompletionAdmin(admin.ModelAdmin):
    model = SurveyCompletion
    fields = ("survey", "user", "times_completed", "created_at", "updated_at")
    readonly_fields = ["created_at", "updated_at"]

    search_fields = ("user__username", "user__anon_username", "survey__type")
    list_display = ("user", "anon_username", "survey", "times_completed", "created_at", "updated_at")
    list_filter = ("survey",)

    def anon_username(self, obj):
        return obj.user.anon_username
