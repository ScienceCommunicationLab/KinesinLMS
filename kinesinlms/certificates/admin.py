from django.contrib import admin

from kinesinlms.certificates.models import Signatory, CertificateTemplate, Certificate


class SignatoryInline(admin.TabularInline):
    model = CertificateTemplate.signatories.through
    extra = 0


@admin.register(Signatory)
class SignatoryAdmin(admin.ModelAdmin):
    model = Signatory


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    model = CertificateTemplate
    inlines = [SignatoryInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    model = Certificate
    list_display = ('student', 'certificate_template', 'uuid', "created_at")
