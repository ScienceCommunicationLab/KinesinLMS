from rest_framework.relations import SlugRelatedField
from rest_framework.serializers import ModelSerializer

from kinesinlms.badges.models import BadgeAssertion, BadgeClass, BadgeProvider


class BadgeAssertionSerializer(ModelSerializer):
    class Meta:
        model = BadgeAssertion
        fields = ('badge_class',
                  'recipient',
                  'achieved',
                  'achieved_date',
                  'item_slugs'
                  )


class BadgeClassSerializer(ModelSerializer):
    provider = SlugRelatedField(slug_field='slug',
                                queryset=BadgeProvider.objects.all(),
                                many=False)

    class Meta:
        model = BadgeClass
        fields = ("slug",
                  "type",
                  "name",
                  "provider",
                  "external_entity_id",
                  "open_badge_id",
                  "image_url",
                  "description",
                  "criteria")
