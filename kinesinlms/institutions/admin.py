from django.contrib import admin

from kinesinlms.institutions.models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    model = Institution
    list_display = ('id', 'slug', 'name')
