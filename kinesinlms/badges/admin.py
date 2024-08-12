from django.contrib import admin

from kinesinlms.badges.models import BadgeClass, BadgeAssertion, BadgeProvider


class BadgeAssertionInline(admin.TabularInline):
    model = BadgeAssertion
    extra = 0


@admin.register(BadgeClass)
class BadgeClassAdmin(admin.ModelAdmin):
    model = BadgeClass
    list_display = ['id', 'name', 'provider', 'external_entity_id', 'image_url', 'description', 'course']
    list_display_links = ['id', ]
    inlines = [BadgeAssertionInline, ]


@admin.register(BadgeAssertion)
class BadgeAssertionAdmin(admin.ModelAdmin):
    model = BadgeAssertion
    list_display = ['id', 'badge_class', 'recipient', 'issued_on', 'open_badge_id', 'error_message']
    list_display_links = ['id', ]


@admin.register(BadgeProvider)
class BadgeProviderAdmin(admin.ModelAdmin):
    model = BadgeProvider
    list_display = ['id', 'name', 'slug', 'api_url', 'issuer_entity_id', 'salt']
    list_display_links = ['id', ]
