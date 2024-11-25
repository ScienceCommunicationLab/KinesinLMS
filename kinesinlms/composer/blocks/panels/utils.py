from django.template.loader import render_to_string

from kinesinlms.learning_library.models import Resource, ResourceType


def get_jupyter_wrapper_html(
    resource: Resource | None,
    course,
    block,
    block_resource,
) -> str:
    """
    Returns the HTML for the Jupyter Notebook wrapper shown in the panel.
    """
    if resource and not resource.type == ResourceType.JUPYTER_NOTEBOOK.name:
        raise ValueError(f"Expected Jupyter Notebook Resource (got {resource})")

    context = {
        "resource": resource,
        "course": course,
        "block": block,
        "block_resource": block_resource,
    }

    return render_to_string("composer/blocks/jupyter/jupyter_selector.html", context)
