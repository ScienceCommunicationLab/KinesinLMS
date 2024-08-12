from django import forms

from kinesinlms.educator_resources.models import EducatorSurvey


class EducatorSurveyForm(forms.ModelForm):
    class Meta:
        model = EducatorSurvey
        fields = ['plan_to_use', 'evaluating', 'email']
        labels = {
            'plan_to_use': 'How will you use these resources?',
            "evaluating": "Are you planning on evaluating?",
            "email": "Email (not required)"
        }
        widgets = {
          'plan_to_use': forms.Textarea(attrs={'rows': 1, 'cols': 15}),
        }
