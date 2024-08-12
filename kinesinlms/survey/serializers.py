from rest_framework import serializers

from kinesinlms.survey.models import Survey, SurveyProvider


class SurveySerializer(serializers.ModelSerializer):
    days_delay = serializers.IntegerField(required=False)
    provider = serializers.SlugRelatedField(slug_field='slug',
                                            many=False,
                                            queryset=SurveyProvider.objects.all(),
                                            required=False)

    class Meta:
        model = Survey
        fields = ('type',
                  'send_reminder_email',
                  'provider',
                  'days_delay',
                  'survey_id',
                  'url')

    def validate(self, data):
        data = super().validate(data)
        return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        return instance
