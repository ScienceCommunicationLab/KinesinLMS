from django.contrib import admin

from kinesinlms.external_tools.models import ExternalToolProvider


@admin.register(ExternalToolProvider)
class ExternalToolProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'lti_version', 'type')
    search_fields = ('name', 'description')
    list_filter = ('lti_version', 'type')
