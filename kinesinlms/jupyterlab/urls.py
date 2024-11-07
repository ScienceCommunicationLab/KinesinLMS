from django.urls import path

from . import views as jupyterlab_views

app_name = "jupyter_hub"
urlpatterns = [
    path(
        "jupyterlab_view/<int:pk>/",
        jupyterlab_views.launch_jupyterlab_view,
        name="launch_jupyterlab_view",
    ),
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "jupyterlab_view/<int:pk>/",
        jupyterlab_views.launch_jupyterlab_view_hx,
        name="launch_jupyterlab_view_hx",
    ),
]
