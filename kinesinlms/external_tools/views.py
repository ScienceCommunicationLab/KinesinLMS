import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render

from kinesinlms.external_tools.models import ExternalToolProviderType, ExternalToolView
from kinesinlms.external_tools.service.base_service import BaseExternalToolService
from kinesinlms.external_tools.service.factory import ExternalToolServiceFactory
from kinesinlms.learning_library.models import Block, BlockType

logger = logging.getLogger(__name__)


def launch_jupyter_lab_view_hx(request, pk):
    """
    Launches the JupyterLab external tool in an iframe
    """

    block = get_object_or_404(Block, type=BlockType.JUPYTER_LAB.name, pk=pk)

    try:
        # Get the appropriate service based on the provider type
        service: BaseExternalToolService = ExternalToolServiceFactory.create_service(
            tool_type=ExternalToolProviderType.JUPYTER_LAB.name
        )

        # Use the service to generate the launch URL
        external_tool_launch_url = service.get_launch_url()

    except Exception as e:
        logger.exception(
            f"Error launching {ExternalToolProviderType.JUPYTER_LAB.name} view",
            extra={
                "block": block,
            },
        )
        return HttpResponseBadRequest(str(e))

    template = "external_tools/jupyter_lab_view_hx.html"
    context = {
        "jupyter_lab_launch_url": external_tool_launch_url,
    }
    return render(request, template, context)


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
