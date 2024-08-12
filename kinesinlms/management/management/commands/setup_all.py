# Custom command to set up default forums and forum permissions
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

import logging

from kinesinlms.management.permissions import setup_initial_permissions
from kinesinlms.management.utils import setup_waffle
from kinesinlms.users.utils import create_default_groups

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Run all 'setup' commands after migrating an empty database when first setting up an KinesinLMS site.
    """

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=stdout, stderr=stderr, no_color=no_color)

    def handle(self, *args, **options):
        self.stdout.write("Setting up all initial data and settings.")

        self.stdout.write("Setting up KinesinLMS: ")
        self.stdout.write("-----------------------------")
        self.stdout.write("  ")
        create_default_groups()

        self.stdout.write("  ")
        setup_waffle()

        self.stdout.write("  ")
        setup_initial_permissions()
        
        self.stdout.write("  ")

        if settings.DJANGO_PIPELINE == 'LOCAL':
            self._configure_site_for_local()

        self.stdout.write("DONE setting up KinesinLMS")

    def _configure_site_for_local(self):
        # When running in localhost, the Site object should have its domain set to
        # localhost so the cookie detection works properly.

        site = Site.objects.get_current()
        self.stdout.write("  - Configuring for local development: {site.domain}")
        if site.domain != 'localhost':
            site.domain = 'localhost'
            site.save()
            self.stdout.write("     -- Set site domain to localhost")
        self.stdout.write("  - DONE Configuring for local development: {site.domain}")
