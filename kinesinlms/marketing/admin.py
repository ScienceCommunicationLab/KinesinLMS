from django.contrib import admin

from kinesinlms.marketing.models import Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    model = Testimonial
    list_display = (
        "id",
        "quote",
        "name",
        "title",
        "company",
        "image",
        "course",
        "visible",
    )
