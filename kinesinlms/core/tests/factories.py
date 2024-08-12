from factory.django import DjangoModelFactory

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.core.models import SiteProfile


class SiteProfileFactory(DjangoModelFactory):
    class Meta:
        model = SiteProfile

    support_email = "support@example.com"


class CourseCatalogDescriptionFactory(DjangoModelFactory):
    class Meta:
        model = CourseCatalogDescription
        django_get_or_create = ('name',)

    title = "Some Course"
    blurb = "A blurb for some course."
    overview = "An overview for some course."
    about_content = "About content for some course."
    sidebar_content = "Some sidebar content"
    thumbnail = "some_thumbnail.png"
    visible = True
    hex_theme_color = None
    custom_stylesheet = "some-course.css"
    trailer_video_url = None
    effort = "300 hours/week"
    duration = "5 weeks"
    order = 2
