from django.contrib import admin

# Register your models here.
from kinesinlms.tracking.models import TrackingEvent


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    model = TrackingEvent
    list_display = (
        "id",
        "uuid",
        "event_type",
        "time",
        "user",
        "anon_username",
        "course_slug",
        "course_run",
    )
    search_fields = [
        "event_type",
        "user__username",
        "anon_username",
        "course_slug",
        "course_run",
    ]
