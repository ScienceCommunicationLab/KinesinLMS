from django.forms import ModelForm

from kinesinlms.badges.models import BadgeAssertion, BadgeProvider


class BadgeAssertionForm(ModelForm):
    class Meta:
        model = BadgeAssertion
        fields = ['badge_class', 'recipient']


class BadgeProviderForm(ModelForm):
    class Meta:
        model = BadgeProvider
        fields = [
            'active',
            'name',
            'type',
            'slug',
            'api_url',
            'salt',
            'issuer_entity_id',
            'access_token',
            'refresh_token'
        ]
