

from factory.django import DjangoModelFactory

from kinesinlms.marketing.models import Testimonial


class TestimonialFactory(DjangoModelFactory):

    class Meta:
        model = Testimonial

    visible = True
    name = "Somebody"
    company = "Some Company"
    quote = "Such an awesome course"

