from django.forms import ModelForm

from kinesinlms.forum.models import ForumProvider


class ForumProviderForm(ModelForm):
    class Meta:
        model = ForumProvider
        fields = [
            "active",
            "type",
            "forum_url",
            "forum_api_username",
            "enable_sso",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.save()
        return instance

