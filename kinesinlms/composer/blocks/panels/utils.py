from django.template.loader import render_to_string

from kinesinlms.learning_library.models import Resource


def get_jupyter_wrapper_html(
    attached_notebook: Resource | None,
    course,
    block,
) -> str:
    """
    Returns the HTML for the Jupyter Notebook wrapper shown in the panel.
    """
    if (
        attached_notebook
        and not attached_notebook.type == Resource.ResourceType.JUPYTER_NOTEBOOK
    ):
        raise ValueError(
            f"Expected Jupyter Notebook Resource (got {attached_notebook})"
        )

    context = {
        "attached_notebook": attached_notebook,
        "course": course,
        "block": block,
    }

    return render_to_string("composer/blocks/jupyter/jupyter_selector.html", context)
