# Create your views here.
import logging
from typing import Dict, List

from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from kinesinlms.jupyterlab.service import JupyterLabService, TooManyNotebooksError
from kinesinlms.learning_library.models import Block, BlockType, ResourceType

logger = logging.getLogger(__name__)


def launch_jupyterlab_view(request, pk):
    """
    Launches the JupyterLab tool and then redirect to it.
    """

    err_msg = None
    try:
        jupyterlab_url = _get_jupyter_lab_url(request, pk)
    except TooManyNotebooksError as e:
        err_msg = _("Too many notebooks are currently running. Please try again later.")
    except Exception as e:
        logger.exception(f"Error launching JupyterLab view. {e}")
        err_msg = _("Error launching JupyterLab view. Please try again later.")

    if err_msg:
        context = {"error_message": err_msg}
        return render(
            request,
            "course/blocks/jupyterlab/jupyterlab_error_hx.html",
            context,
        )
    else:
        return redirect(jupyterlab_url)


def launch_jupyterlab_view_hx(request, pk):
    """
    Launches the JupyterLab external tool in an iframe
    """

    jupyterlab_url = _get_jupyter_lab_url(request, pk)

    template = "course/blocks/jupyterlab/jupyterlab_view_hx.html"
    context = {
        "jupyterlab_launch_url": jupyterlab_url,
    }
    return render(request, template, context)


def _get_jupyter_lab_url(request, pk):
    block = get_object_or_404(
        Block,
        type=BlockType.JUPYTER_LAB.name,
        pk=pk,
    )

    # Get the appropriate service based on the provider type
    service = JupyterLabService()

    # See if we have a default notebook attached
    notebook_resources = block.resources.filter(type=ResourceType.JUPYTER_NOTEBOOK.name)
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

    # Get basic resource info to sent to JupyterLab
    # in a form it recognizes
    resources: List[Dict] = [
        resource.info
        for resource in block.resources.all()
        if resource.type != ResourceType.JUPYTER_NOTEBOOK.name
    ]

    # Use the service to generate the launch URL
    jupyterlab_launch_url = service.get_launch_url(
        notebook_filename=notebook_filename,
        resources=resources,
    )

    return jupyterlab_launch_url
