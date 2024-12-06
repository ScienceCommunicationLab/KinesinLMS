from rest_framework import serializers

from kinesinlms.marketing.models import Testimonial


class TestimonialSerializer(serializers.ModelSerializer):
    course = serializers.StringRelatedField(source="course.display_name")

    class Meta:
        model = Testimonial
        fields = (
            "quote",
            "name",
            "company",
            "title",
            "image",
            "course",
        )
