# Create your views here.
import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render

from kinesinlms.jupyterlab.service import JupyterLabService
from kinesinlms.learning_library.models import Block, BlockType, ResourceType

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

        # See if we have a default notebook attached
        notebook_resources = block.resources.filter(
            type=ResourceType.JUPYTER_NOTEBOOK.name
        )
        if notebook_resources.count() >= 1:
            if notebook_resources.count() > 1:
                logger.error(
                    "Multiple Jupyter Notebook resources found for block. Using first.",
                    extra={
                        "block": block,
                    },
                )
            notebook_resource = notebook_resources.first()
        else:
            notebook_resource = None

        notebook_filename = None
        if notebook_resource:
            if not notebook_resource.resource_file:
                logger.error(
                    "Jupyter Notebook resource has no resource_file attached. "
                    "Launching JupyterLab without a notebook."
                )
            notebook_filename = notebook_resource.resource_file.name.split("/")[-1]

        # Use the service to generate the launch URL
        jupyterlab_launch_url = service.get_launch_url(
            notebook_filename=notebook_filename
        )

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