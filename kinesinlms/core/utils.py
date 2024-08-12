import binascii
import logging

import boto3
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from lxml.html.clean import Cleaner

from kinesinlms.core.models import SiteProfile

logger = logging.getLogger(__name__)
# ~~~~~~~~~~~~~~~~~~~~
# AWS CLIENTS
# ~~~~~~~~~~~~~~~~~~~~

# Defined here so available in all apps

aws_lamba_client = None
aws_dynamodb_resource = None


def get_current_site_profile() -> SiteProfile:
    if settings.SITE_ID:
        site = Site.objects.get(id=settings.SITE_ID)
        if hasattr(site, 'profile'):
            return site.profile
        else:
            site_profile = SiteProfile.objects.get_or_create(site=site)[0]
            return site_profile
    else:
        logger.info("No SITE_ID set in settings. Using default site profile.")
        try:
            return SiteProfile.objects.get(id=1)
        except SiteProfile.DoesNotExist:
            logger.error("No default site profile found.")
            return SiteProfile.objects.get_or_create(site=1)[0]


def get_aws_lambda_client():
    global aws_lamba_client
    if not aws_lamba_client:
        aws_lamba_client = boto3.client('lambda',
                                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                        region_name="us-west-1")
    return aws_lamba_client


def get_aws_dynamodb_resource():
    global aws_dynamodb_resource
    if not aws_dynamodb_resource:
        aws_dynamodb_resource = boto3.resource('dynamodb',
                                               aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                               aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                               region_name="us-west-1")
    return aws_dynamodb_resource


def clean_html(html_text):
    assert html_text is not None
    cleaner = Cleaner(style=True)
    return cleaner.clean_html(html_text)


def truncate_string(input_str: str, max_length: int = 50):
    ellip = '...'
    if len(input_str) > max_length:
        return input_str[:max_length - len(ellip)] + ellip
    return input_str


def get_domain() -> str:
    current_site = get_current_site(None)
    return current_site.domain


def is_valid_hex_string(s):
    try:
        binascii.unhexlify(s)
        return True
    except binascii.Error:
        return False
