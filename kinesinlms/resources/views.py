import logging

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from kinesinlms.resources.models import GenericResource, GenericResourceType

logger = logging.getLogger(__name__)


def generic_resource(request, resource_uuid: str):
    """
    Simple view to 'generic' resources ... a catch-all for media files
    that need a publicly accessible URL.
    """
    resource: GenericResource = get_object_or_404(GenericResource, uuid=resource_uuid)

    if resource.resource_type != GenericResourceType.PDF.name:
        logger.exception(f"Unsupported generic resource type: {resource.resource_type}")
        raise Http404()

    filename = resource.file.name.split('/')[-1]
    response = HttpResponse(resource.file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename

    return response
