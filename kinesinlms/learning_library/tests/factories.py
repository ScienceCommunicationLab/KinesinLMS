import factory

from kinesinlms.learning_library.models import Block, BlockStatus, UnitBlock


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Block

    display_name = factory.Sequence(lambda n: f"Unit {n}")
    short_description = factory.LazyAttribute(lambda o: f"This is a short description of Unit {o.display_name}")
    status = BlockStatus.PUBLISHED.name


class UnitBlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UnitBlock

    slug = factory.LazyAttribute(lambda o: f"unit-block-{o}")
    label = factory.LazyAttribute(lambda o: f"Unit Block {o}")
