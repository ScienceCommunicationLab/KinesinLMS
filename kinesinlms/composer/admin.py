from django.contrib import admin

# Register your models here.
from kinesinlms.composer.models import EditStatus


@admin.register(EditStatus)
class EditStatusAdmin(admin.ModelAdmin):
    model = EditStatus
    list_display = ('id', 'course', 'mode')
