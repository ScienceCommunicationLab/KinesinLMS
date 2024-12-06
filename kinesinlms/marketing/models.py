from django.db import models
from django.utils.translation import gettext_lazy as _
from PIL import Image

from kinesinlms.core.models import Trackable
from kinesinlms.course.models import Course


class Testimonial(Trackable):
    visible = models.BooleanField(default=True)
    quote = models.TextField(null=False)
    name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_(
            "The name of the person giving the testimonial. This can be generic like 'student' or 'industry professional'"
        ),
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    company = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to="testimonials/", null=True, blank=True)

    # A testimonial can be associated with a course
    # ...if not it's just a general testimonial.
    course = models.ForeignKey(Course, null=True, blank=True, related_name="testimonials", on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"

    def save(self, *args, **kwargs):
        super(Testimonial, self).save(*args, **kwargs)

        if self.image:
            img = Image.open(self.image.path)

            if img.height > 200 or img.width > 200:
                output_size = (200, 200)
                img.thumbnail(output_size)
                img.save(self.image.path)
