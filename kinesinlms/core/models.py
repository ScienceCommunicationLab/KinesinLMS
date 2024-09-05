from django.contrib.sites.models import Site
from django.db import models
import uuid


class Trackable(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteProfile(models.Model):
    site = models.OneToOneField(Site, related_name="profile", on_delete=models.CASCADE)

    uuid = models.UUIDField(
        default=uuid.uuid4,
        null=True,
        blank=False,
        editable=True,
        help_text="A unique uuid identifier for this site.",
    )

    facebook_url = models.URLField(
        blank=True, null=True, help_text="URL of the Facebook page for this site."
    )

    twitter_username = models.CharField(
        max_length=50, blank=True, help_text="Twitter username without the @ symbol."
    )

    support_email = models.EmailField(
        blank=True, null=True, help_text="Email address for support requests."
    )

    newsletter_signup_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL for a basic ewsletter signup form, ostensibly on a "
        "third-party email automation provider.",
    )

    educators_newsletter_signup_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL for an educators newsletter signup form, ostensibly on a "
        "third-party email automation provider.",
    )

    def save(self, *args, **kwargs):
        if not self.site:
            self.site = Site.objects.get_current()
        if not self.uuid:
            self.uuid = uuid.uuid4()
        super().save(*args, **kwargs)