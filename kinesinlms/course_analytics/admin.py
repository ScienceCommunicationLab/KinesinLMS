from django.contrib import admin

from kinesinlms.course_analytics.models import StudentProgressReport


# Register your models here.

@admin.register(StudentProgressReport)
class StudentProgressReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'cohort')
    model = StudentProgressReport
