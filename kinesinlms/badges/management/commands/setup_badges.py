"""
This command sets up badges models and configures certain courses to enable badges.

It *does not* enable badges on existing users. Those users will need to be contacted to
manually enable badges in the new "Profile" section.


"""

import logging

from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from kinesinlms.badges import utils

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create basic badge classes needed for KinesinLMS."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-r", "--remote", type=str)

    def handle(self, *args, **options):
        utils.setup_badges()
