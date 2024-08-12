import bleach
from rest_framework import serializers


class SanitizedHTMLField(serializers.CharField):
    def to_internal_value(self, data):
        """
        Sanitize the HTML content before saving it.
        """

        cleaned_data = bleach.clean(
            data,
            tags=bleach.sanitizer.ALLOWED_TAGS,
            attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
            strip=True,
            strip_comments=True,
        )
        return cleaned_data
