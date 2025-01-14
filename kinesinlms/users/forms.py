import datetime

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.conf import settings
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import forms as user_forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from kinesinlms.users.models import User, UserSettings


def current_year():
    return datetime.date.today().year


def year_choices():
    return [(r, r) for r in range(1900, datetime.date.today().year + 1)]


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserChangeForm(user_forms.UserChangeForm):
    class Meta(user_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(user_forms.UserCreationForm):
    error_message = user_forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    class Meta(user_forms.UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])


class UserSettingsForm(forms.ModelForm):
    enable_badges = forms.BooleanField(
        required=False,
        help_text=_("Check this option if you want to receive badges " "in courses that award them."),
    )

    class Meta:
        model = UserSettings
        fields = ("enable_badges",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.help_text_inline = False
        self.helper.attrs = {"novalidate": ""}
        self.helper.form_method = "post"  # get or post method
        self.helper.form_id = "user_settings"
        self.helper.form_class = "user_settings_form"
        self.helper.add_input(Submit("submit", "Save"))


class UserSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            "name",
            "informal_name",
            "career_stage",
            "year_of_birth",
            "gender",
            "gender_description",
            "agree_to_honor_code",
            "enable_badges",
        )
        if settings.USE_RECAPTCHA:
            fields = fields + ("captcha",)

    # Override the init method
    def __init__(self, *args, **kwargs):
        # Call the init of the parent class
        super().__init__(*args, **kwargs)
        # Remove autofocus because it is in the wrong place
        del self.fields["username"].widget.attrs["autofocus"]
        self.fields["email"].widget.attrs["autofocus"] = True

    error_message = UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    if settings.USE_RECAPTCHA:
        captcha = ReCaptchaField(
            widget=ReCaptchaV2Checkbox(
                attrs={
                    "data-theme": "light",  # default=light
                    "data-size": "normal",  # default=normal
                },
            ),
        )

    name = forms.CharField(max_length=500, label="Full name", required=False)

    informal_name = forms.CharField(
        max_length=255,
        label="What shall we call you (for example, when we send you mail)?",
        required=False,
    )

    gender_description = forms.CharField(
        max_length=100,
        label="If none of the gender options above apply to " "you, please describe your gender:",
        required=False,
    )

    year_of_birth = forms.TypedChoiceField(coerce=int, choices=year_choices, initial=current_year, required=False)

    # Make sure box is ticked for signup...
    agree_to_honor_code = forms.BooleanField(
        required=True,
        label=mark_safe(
            _(
                "I agree to the KinesinLMS <a href='/tos'>"
                "Terms of Service</a> and <a href='/honor_code/'>"
                "Honor Code</a>"
            )
        ),
    )

    # Make sure box is ticked for signup...
    enable_badges = forms.BooleanField(
        required=True,
        initial=True,
        label=mark_safe(
            _("Enable course badges <a href='/help/badges/' target='_blank'>" "What are course badges?</a>")
        ),
    )

    def signup(self, request, user):  # noqa: F841
        user.name = self.cleaned_data["name"]
        user.informal_name = self.cleaned_data["informal_name"]
        user.career_stage = self.cleaned_data["career_stage"]
        user.year_of_birth = self.cleaned_data["year_of_birth"]
        user.gender = self.cleaned_data["gender"]
        user.gender_description = self.cleaned_data["gender_description"]
        user.agree_to_honor_code = self.cleaned_data["agree_to_honor_code"]
        user_settings: UserSettings = user.get_settings()
        user_settings.enable_badges = self.cleaned_data["enable_badges"]
        user_settings.save()
        user.save()
