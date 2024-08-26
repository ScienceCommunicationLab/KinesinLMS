from django.urls import path

from . import views

app_name = "lti"
urlpatterns = [
    # LTIv1.3 LOGIN ROUTE
    # URL to initiate the LTI v1.3 OIDC login process.
    # This route should redirect the user to the tool's login initiation URL.
    path(
        "launch/<slug:course_slug>/<slug:course_run>/<int:course_unit>/<int:block_id>/",
        views.lti_launch,
        name="lti_launch",
    ),
    # LTIv1.3 REDIRECT ROUTE
    # After we initiate the tool launch by sending the user to the tool's login initiation URL,
    # it will direct the user back to our site at this URL as it starts the OIDC login process.
    # This route should continue that process (if all is well) by launching an auto-submitting form
    # that sends the user to the redirect ('launch') url on the tool.
    path(
        "authorize_redirect/",
        views.lti_authorize_redirect,
        name="lti_authorize_redirect",
    ),
    # JWKS for a tool provider
    path("security/jwks/", views.jwks_info_view, name="jwks"),
]
