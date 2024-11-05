from django.urls import path

from . import views as external_tools_views

app_name = "external_tools"
urlpatterns = [
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path(
        "external_tool_view/<int:pk>/",
        external_tools_views.launch_external_tool_view_hx,
        name="launch_external_tool_view_hx",
    ),
    path(
        "jupyter_lab_view/<int:pk>/",
        external_tools_views.launch_jupyter_lab_view_hx,
        name="launch_jupyter_lab_view_hx",
    ),
]
