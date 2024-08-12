from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):

    careerStage = serializers.CharField(source="career_stage")

    class Meta:
        model = User
        fields = ('id', 'gender', 'careerStage')

    def to_representation(self, instance):
        my_fields = {'gender', 'careerStage'}
        data = super().to_representation(instance)
        for field in my_fields:
            try:
                if not data[field]:
                    data[field] = ""
            except KeyError:
                pass
        return data


class ImportV1UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'email', 'gender', 'career_stage',)

    def validate_username(self, value):
        """
        Make sure user doesn't exist
        """
        user = User.objects.get(username=value)
        if user:
            raise serializers.ValidationError("User already exists")
        return value

