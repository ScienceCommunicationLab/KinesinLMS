from rest_framework import serializers

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.marketing.serializers import TestimonialSerializer


class CourseCatalogDescriptionSerializer(serializers.ModelSerializer):
    """
    Handles serialization/de-serialization of CourseCatalogDescription objects.

    NOTE:
        Does not concern itself with syllabus or thumbnail. Those are file objects
        and handled by the greater import/export logic.

    """

    # Testimonials seem very site dependent, so we don't read in
    # testimonials. They have to be set up separately after a course import.
    testimonials = TestimonialSerializer(
        many=True,
        read_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CourseCatalogDescription
        fields = (
            "title",
            "blurb",
            "overview",
            "about_content",
            "testimonials",
            "sidebar_content",
            "visible",
            "hex_theme_color",
            "hex_title_color",
            "custom_stylesheet",
            "trailer_video_url",
            "effort",
            "duration",
            "audience",
            "features",
            "order",
            # "thumbnail",
            # "syllabus",
        )
