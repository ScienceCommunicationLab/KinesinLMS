import factory

from kinesinlms.learning_library.models import Block, BlockStatus


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Block

    display_name = factory.Sequence(lambda n: f"Unit {n}")
    short_description = factory.LazyAttribute(lambda o: f"This is a short description of Unit {o.display_name}")
    status = BlockStatus.PUBLISHED.name

