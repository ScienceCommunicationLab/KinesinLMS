from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from django.core import validators


@deconstructible
class KinesinLMSUnicodeUsernameValidator(validators.RegexValidator):
    # Derived from UnicodeUsernameValidator but we removed the @ character.
    # We do this because Discourse doesn't like usernames with @ in them.

    regex = r'^[\w.+-]+$'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and ./+/-/_ characters.'
    )
    flags = 0


custom_username_validators = [KinesinLMSUnicodeUsernameValidator()]
