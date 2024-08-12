from django.contrib.auth import get_user_model
from django.forms import Form

from kinesinlms.composer.models import ComposerSettings
from kinesinlms.learning_library.models import UnitBlock, Block

User = get_user_model()


class BasePanelForm(Form):
    """
    Base form class for editing one or more properties of a Block or item
    related to a Block (e.g. Assessment) in a
    """

    def __init__(self,
                 *args,
                 block: Block = None,
                 unit_block: UnitBlock = None,
                 user=None,
                 **kwargs):
        if not block:
            raise ValueError("block cannot be None")
        if not unit_block:
            raise ValueError("unit_block cannot be None")
        if not user:
            raise ValueError("user cannot be None")
        self.block: Block = block
        self.unit_block: UnitBlock = unit_block
        self.user = user
        self.settings = ComposerSettings.objects.get_or_create(user=user)[0]
        super().__init__(*args, **kwargs)

    def save(self):
        pass
