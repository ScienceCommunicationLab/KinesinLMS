from django.urls import path

from . import views

app_name = "discourse"

urlpatterns = [
    path("sso", views.discourse_sso, name="discourse-sso"),
    path("activity_callback", views.activity_callback, name="discourse-activity-callback")
]
