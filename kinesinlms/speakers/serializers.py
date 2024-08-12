import logging

from rest_framework import serializers

from kinesinlms.speakers.models import Speaker

logger = logging.getLogger(__name__)


class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speaker
        fields = ('first_name',
                  'last_name',
                  'full_name',
                  'video_url',
                  'slug',
                  'suffix',
                  'title',
                  'identities',
                  'institution',
                  'pronouns',
                  'bio')

    def validate_slug(self, data):
        logger.info("test")
        return data

    def validate(self, data):
        slug = data['slug']
        if Speaker.objects.filter(slug=slug).exists():
            # Speaker will be linked via slug
            return data
        return super().validate(data)

    def create(self, validated_data):
        logger.info("create()")
        return super().create(validated_data)
