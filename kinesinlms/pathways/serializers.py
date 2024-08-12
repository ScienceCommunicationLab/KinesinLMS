
from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from kinesinlms.pathways.models import Pathway


class PathwaySerializer(TaggitSerializer, serializers.ModelSerializer):

    tags = TagListSerializerField()

    class Meta:
        model = Pathway
        fields = ('display_name', 'description', 'tags', 'author')


class IndividualPathwaySerializer(serializers.ModelSerializer):

    class Meta:
        model = Pathway
        fields = ('display_name', 'description', 'tags', 'author', 'content_structure')
