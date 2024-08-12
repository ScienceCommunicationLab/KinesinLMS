from django.contrib import admin

from kinesinlms.management.models import ManualEnrollment


# Register your models here.
@admin.register(ManualEnrollment)
class ManualEnrollmentAdmin(admin.ModelAdmin):
    model = ManualEnrollment
    list_display = ('id', 'course', 'cohort', 'user')
