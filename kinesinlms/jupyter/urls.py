from django.urls import path

from . import views as jupyter_views

app_name = "jupyter_hub"
urlpatterns = [
    path(
        "jupyter_views/<int:pk>/",
        jupyter_views.launch_jupyter_view,
        name="launch_jupyter_view",
    ),
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "jupyter_views/<int:pk>/",
        jupyter_views.launch_jupyter_view_hx,
        name="launch_jupyter_view_hx",
    ),
]
