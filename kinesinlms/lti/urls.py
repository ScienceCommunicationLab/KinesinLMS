from django.urls import path

from . import views

app_name = "lti"
urlpatterns = [

    # We don't need a 'login' route as we have a template tag that generates
    # the login URL and attaches it to a button in the 'external tool' block.

    # After we initiate the tool launch by sending the user to the tool's login initiation URL,
    # it will direct the user back to our site at this URL as it starts the OIDC login process.
    # This route should continue that process (if all is well) by launching an auto-submitting form
    # that sends the user to the redirect ('launch') url on the tool.
    path('authorize_redirect/', views.lti_authorize_redirect, name='lti_authorize_redirect'),

    # URL to return public JWKS for a tool provider
    path('security/jwks/', views.jwks_info_view, name='jwks')
]
