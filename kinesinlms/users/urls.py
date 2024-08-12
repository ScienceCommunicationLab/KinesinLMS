from django.urls import path

from kinesinlms.users.views import (
    user_list_view,
    user_redirect_view,
    user_update_view,
    user_detail_view,
    UserSettingsView

)

app_name = "users"
urlpatterns = [
    # User
    path("", view=user_list_view, name="list"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    path("<int:pk>/settings/", view=UserSettingsView.as_view(), name="settings"),
]
