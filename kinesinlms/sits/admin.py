from django.contrib import admin

from kinesinlms.sits.models import SimpleInteractiveTool, SimpleInteractiveToolSubmission, SimpleInteractiveToolTemplate


class SimpleInteractiveToolSubmissionInlineAdmin(admin.StackedInline):
    model = SimpleInteractiveToolSubmission
    extra = 0


@admin.register(SimpleInteractiveTool)
class SimpleInteractiveToolAdmin(admin.ModelAdmin):
    model = SimpleInteractiveTool
    list_display = ('id', 'slug', 'tool_type', 'instructions', 'template')
    inlines = (SimpleInteractiveToolSubmissionInlineAdmin,)


@admin.register(SimpleInteractiveToolTemplate)
class SimpleInteractiveToolTemplateAdmin(admin.ModelAdmin):
    model = SimpleInteractiveToolTemplate
    list_display = ('id', 'name', 'tool_type', 'description')


@admin.register(SimpleInteractiveToolSubmission)
class SimpleInteractiveToolSubmissionAdmin(admin.ModelAdmin):
    model = SimpleInteractiveToolSubmission
    list_display = ('id', 'student', 'course', 'simple_interactive_tool', 'status', 'created_at', 'updated_at', 'json_content')
    search_fields = ('student__username',  'status')
