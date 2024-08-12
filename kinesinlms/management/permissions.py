from django.contrib.auth.models import Permission
from enum import Enum
import logging
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group

from kinesinlms.users.models import GroupTypes
logger = logging.getLogger(__name__)


class SitePermissions(Enum):
    """
    These are the names of permissions that control access
    to parts of the KinesinMLS system.

    These permissions aren't directly related to a model,
    so are defined here as an Enum. These values are then
    used to create the permissions.
    """

    CAN_ACCESS_EDUCATOR_RESOURCES = "Can access educator resources"
    CAN_ACCESS_COMPOSER = "Can access composer"


def setup_initial_permissions() -> None:
    """
    Set up the initial permissions for the KinesinLMS application.
    Then, set up the default relationship of permissions to groups.
    In specific:
        - EDUCATOR group gets access to the "Can access educator resources" permission
        - AUTHOR group gets access to the "Can access composer" permission
    
    """

    # In Django, if you want a permission that's not related to a model, you
    # have to use a placeholder contenttype.
    content_type = ContentType.objects.get_for_model(ContentType)  # Placeholder content type
    
    # Make sure default permissions exist...
    logger.info("Creating default permissions:")
    for site_permission in SitePermissions:
        permission, created = Permission.objects.get_or_create(
            codename=site_permission.name,
            name=site_permission.value,
            content_type=content_type
        )
        if created:
            logger.info(f" - created permission: {permission.codename}")
        else:
            logger.info(f" - permission already exists: {permission.codename}")

    # Give groups access to the permissions they need...
    logger.info("Assigning default permissions to groups:")
    try:
        educator_group, created = Group.objects.get_or_create(name=GroupTypes.EDUCATOR.name)
        educator_permission = Permission.objects.get(codename=SitePermissions.CAN_ACCESS_EDUCATOR_RESOURCES.name)
        logger.info(f"  - giving {educator_group} group permission {educator_permission.codename}")
        educator_group.permissions.add(educator_permission)
    except Exception as e:
        logger.exception(f"  - could not assign default permissions for {GroupTypes.EDUCATOR.name}")
        raise e
    
    try:
        author_group, created = Group.objects.get_or_create(name=GroupTypes.AUTHOR.name)
        composer_permission = Permission.objects.get(codename=SitePermissions.CAN_ACCESS_COMPOSER.name)
        logger.info(f"  - giving {author_group} group permission {composer_permission.codename}")
        educator_group.permissions.add(educator_permission)
    except Exception as e:
        logger.exception(f"  - could not assign default permissions for {GroupTypes.EDUCATOR.name}")
        raise e


