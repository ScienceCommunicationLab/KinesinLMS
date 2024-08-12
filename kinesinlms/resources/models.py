import uuid as uuid
from enum import Enum

from django.db import models


class GenericResourceType(Enum):
    PDF = "pdf"


class GenericResource(models.Model):
    """
    A generic resource is just a file that needs to be made accesible to site users.
    Right now that just means PDFs, but it could be anything.
    """
    uuid = models.UUIDField(default=uuid.uuid4,
                            editable=True)
    resource_type = models.CharField(max_length=30,
                                     choices=[(item.name, item.value) for item in GenericResourceType],
                                     null=False,
                                     blank=False)
    file = models.FileField(null=True, blank=True)

    def __str__(self):
        return f"GenericResource: {self.uuid}"
