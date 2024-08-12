from django.forms import ModelForm

from kinesinlms.composer.models import ComposerSettings


class ComposerModelForm(ModelForm):
    """
    Base class for most forms in composer, including those that edit a block.
    """

    def __init__(self, *args, **kwargs):
        """
        We always need a user instance to know how to render certain parts of the form.
        We use this user instance to load that user's ComposerSettings.
        """
        user = kwargs.pop('user', None)
        if not user:
            raise ValueError("user cannot be None")
        self.user = user
        self.settings = ComposerSettings.objects.get_or_create(user=user)[0]
        super().__init__(*args, **kwargs)
