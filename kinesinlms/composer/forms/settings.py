from django.forms import ModelForm

from kinesinlms.composer.models import ComposerSettings


class ComposerSettingsForm(ModelForm):
    class Meta:
        model = ComposerSettings
        fields = [
            # 'html_edit_mode'
        ]
