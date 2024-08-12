from rest_framework import serializers

from kinesinlms.custom_app.models import CustomApp


class CustomAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomApp
        fields = ('display_name',
                  'type',
                  'slug',
                  'short_description',
                  'description',
                  'tab_label')
