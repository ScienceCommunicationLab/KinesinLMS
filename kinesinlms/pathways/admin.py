from django.contrib import admin

# Register your models here.
from kinesinlms.pathways.models import Pathway


@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    model = Pathway
    list_display = ('id', 'display_name', 'author')
    list_display_links = ('id', 'display_name')
    search_fields = ('display_name',)
    list_per_page = 50
