from django.forms import EmailField, ModelForm, TypedChoiceField, RadioSelect

from kinesinlms.users.models import Prospect


class ResourceDownloadForm(ModelForm):
    email = EmailField(required=True,
                       label="Email")

    consent = TypedChoiceField(
        label="I would like to receive information and updates about our scientist training curricula.",
        choices=((1, "Yes"), (0, "No")),
        coerce=lambda x: bool(int(x)),
        widget=RadioSelect,
        initial=None,
        required=True,
    )

    class Meta:
        model = Prospect
        fields = ['email', 'name', 'institution', 'consent']
