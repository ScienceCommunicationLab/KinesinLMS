from django.urls import path

from kinesinlms.users.views import (
    UserSettingsView,
    user_detail_view,
    user_list_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    # User
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("<int:pk>/settings/", view=UserSettingsView.as_view(), name="settings"),
    path("", view=user_list_view, name="list"),
]
