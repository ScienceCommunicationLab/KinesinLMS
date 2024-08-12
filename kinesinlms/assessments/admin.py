from django.contrib import admin

# Register your models here.
from kinesinlms.assessments.models import Assessment, SubmittedAnswer


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    model = Assessment

    list_display = ('id', 'slug', 'question', 'block',
                    'type', 'graded', 'show_slug', 'show_answer')
    list_display_links = ('id', 'slug', 'question')
    search_fields = ('question', 'slug',)
    list_per_page = 50


class AssessmentInlineAdmin(admin.TabularInline):
    model = Assessment


@admin.register(SubmittedAnswer)
class SubmittedAnswerAdmin(admin.ModelAdmin):
    model = SubmittedAnswer

    list_display = ('id', 'assessment_question', 'answer_from_json', 'student', 'status')
    list_display_links = ('id',)
    list_per_page = 50
    actions = ["export_as_csv"]

    def assessment_question(self, obj):
        return obj.assessment.question

    assessment_question.short_description = 'assessment question'

    def answer_from_json(self, obj):
        return obj.json_content.get('answer', None)

    answer_from_json.short_description = 'answer'
