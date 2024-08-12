from rest_framework import serializers
import logging

from kinesinlms.certificates.models import Signatory, CertificateTemplate
logger = logging.getLogger(__name__)


class SignatorySerializer(serializers.ModelSerializer):
    """
    Serializer a Signatory for a Certificate.
    """

    class Meta:
        model = Signatory
        fields = ('slug',
                  'name',
                  'title',
                  'organization')


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """
    Serialize the CertificateTemplate model instance.
    """

    signatories = SignatorySerializer(many=True, required=False)

    class Meta:
        model = CertificateTemplate
        fields = ('signatories', 'custom_template_name')

    def create(self, validated_data):

        signatories_raw_data = validated_data.pop('signatories', None)
        certificate_template = CertificateTemplate.objects.create(**validated_data)

        if signatories_raw_data:
            for signatory_raw_data in signatories_raw_data:
                slug = signatory_raw_data.get('slug', None)
                if slug:
                    signatory, create = Signatory.objects.get_or_create(slug=slug)
                else:
                    signatory = Signatory.objects.create(**signatory_raw_data)
                certificate_template.signatories.add(signatory)

        return certificate_template
