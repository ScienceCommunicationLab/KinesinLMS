from django.db import models
import uuid


class AutoCharField(models.CharField):
    """
    A CharField that automatically generates a UUID4 value if no value is provided.

    Args:
        models (_type_): _description_
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 36)  # assuming UUID length
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if not value:
            value = str(uuid.uuid4())
            setattr(model_instance, self.attname, value)
        return value

