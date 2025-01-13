from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from kinesinlms.pathways.models import Pathway


class PathwayListSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()

    class Meta:
        model = Pathway
        fields = (
            "display_name",
            "description",
            "tags",
            "author",
        )


class PathwaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pathway
        fields = (
            "display_name",
            "author",
            "description",
            "tags",
            "learning_objects",
        )
