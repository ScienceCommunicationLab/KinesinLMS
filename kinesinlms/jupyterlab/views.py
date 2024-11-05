# Create your views here.
import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render

from kinesinlms.jupyterlab.service import JupyterLabService
from kinesinlms.learning_library.models import Block, BlockType

logger = logging.getLogger(__name__)


def launch_jupyterlab_view_hx(request, pk):
    """
    Launches the JupyterLab external tool in an iframe
    """

    block = get_object_or_404(
        Block,
        type=BlockType.JUPYTER_LAB.name,
        pk=pk,
    )

    try:
        # Get the appropriate service based on the provider type
        service = JupyterLabService()

        # Use the service to generate the launch URL
        jupyterlab_launch_url = service.get_launch_url()

    except Exception as e:
        logger.exception(
            "Error launching JupyterLab view",
            extra={
                "block": block,
            },
        )
        return HttpResponseBadRequest(str(e))

    template = "course/blocks/jupyterlab/jupyterlab_view_hx.html"
    context = {
        "jupyterlab_launch_url": jupyterlab_launch_url,
    }
    return render(request, template, context)
