from factory.django import DjangoModelFactory
import os
from django.core.files.base import ContentFile


from kinesinlms.catalog.models import CourseCatalogDescription


class CourseCatalogDescriptionFactory(DjangoModelFactory):
    class Meta:
        model = CourseCatalogDescription

    title = "Some Course"
    blurb = "A blurb for some course."
    overview = "An overview for some course."
    about_content = "About content for some course."
    sidebar_content = "Some sidebar content"
    thumbnail = "some_thumbnail.png"
    visible = True
    hex_theme_color = "ffffff"
    custom_stylesheet = "some-course.css"
    trailer_video_url = None
    effort = "300 hours/week"
    duration = "5 weeks"
    order = 2
    audience = "Test audience"
    features = ["some feature", "another feature"]

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Reference the test files
        thumbnail_path = os.path.join(
            "test/data/catalog_resources", "test_thumbnail.jpg"
        )
        syllabus_path = os.path.join("test/data/catalog_resources", "test_syllabus.pdf")

        # Read the files and create ContentFile instances
        with open(thumbnail_path, "rb") as thumbnail_file:
            kwargs["thumbnail"] = ContentFile(
                thumbnail_file.read(), name="test_thumbnail.jpg"
            )

        with open(syllabus_path, "rb") as syllabus_file:
            kwargs["syllabus"] = ContentFile(
                syllabus_file.read(), name="test_syllabus.pdf"
            )

        return super()._create(model_class, *args, **kwargs)
