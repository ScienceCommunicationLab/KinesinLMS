from django.contrib import admin

# Register your models here.
from kinesinlms.resources.models import GenericResource
from kinesinlms.users.models import Prospect


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    model = Prospect
    list_display = ['id', 'email', 'consent']


@admin.register(GenericResource)
class GenericResourceAdmin(admin.ModelAdmin):
    model = GenericResource
    list_display = ['id', 'uuid', 'resource_type']
