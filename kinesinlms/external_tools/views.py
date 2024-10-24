import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render

from kinesinlms.external_tools.models import ExternalToolView
from kinesinlms.external_tools.service.base_service import BaseExternalToolService
from kinesinlms.external_tools.service.factory import ExternalToolServiceFactory

logger = logging.getLogger(__name__)


def launch_external_tool_view_hx(request, pk):
    """
    Launches the external tool in a new window.
    """
    external_tool_view = get_object_or_404(ExternalToolView, pk=pk)

    try:
        # Get the appropriate service based on the provider type
        service: BaseExternalToolService = ExternalToolServiceFactory.create_service(
            external_tool_view.external_tool_provider.type
        )

        # Use the service to generate the launch URL
        external_tool_launch_url = service.get_launch_url(external_tool_view)

    except Exception as e:
        logger.exception(
            "Error launching external tool view",
            extra={
                "external_tool_view": external_tool_view,
            },
        )
        return HttpResponseBadRequest(str(e))

    template = "external_tools/external_tool_view_hx.html"
    context = {
        "external_tool_view": external_tool_view,
        "external_tool_launch_url": external_tool_launch_url,
    }
    return render(request, template, context)
