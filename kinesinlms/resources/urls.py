from django.urls import path

from . import views

app_name = "resources"
urlpatterns = [

    path("g/<uuid:resource_uuid>/",
         views.generic_resource,
         name="generic_resource")
]
