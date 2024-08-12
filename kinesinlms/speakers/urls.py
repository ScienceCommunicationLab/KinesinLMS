from django.urls import path

from kinesinlms.speakers import views

app_name = "speakers"

urlpatterns = [
    path("", views.speakers_list, name="speakers-list"),
    path("<slug:speaker_slug>", views.speaker_detail, name="speaker-detail"),
]
