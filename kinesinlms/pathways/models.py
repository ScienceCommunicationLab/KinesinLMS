
from django.db import models
from django.conf import settings

from taggit.managers import TaggableManager
from kinesinlms.core.models import Trackable
from kinesinlms.learning_library.models import Block


class Pathway(Trackable):
    display_name = models.CharField(max_length=250,
                                    default=None,
                                    null=True,
                                    blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               blank=False,
                               null=False,
                               related_name='pathways',
                               on_delete=models.CASCADE)
    description = models.TextField(default=None,
                                   null=True,
                                   blank=True)
    tags = TaggableManager()

    learning_objects = models.ManyToManyField(Block,
                                              through='PathStep',
                                              related_name='path_steps')


class PathStep(Trackable):
    order = models.IntegerField(default=0)
    pathway = models.ForeignKey(Pathway, on_delete=models.CASCADE)
    learning_object = models.ForeignKey(Block, on_delete=models.CASCADE)

