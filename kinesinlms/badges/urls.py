from django.urls import path
from . import views

app_name = "badges"
urlpatterns = [

    path('',
         views.BadgeClassListView.as_view(),
         name="badge_class_list"),

    path('<int:pk>/create_assertion',
         views.BadgeAssertionFormView.as_view(),
         name="create_badge_class_assertion"),

    path('<int:pk>/',
         views.BadgeClassDetailView.as_view(),
         name="badge_class_detail"),

    path('<int:badge_class_id>/assertion/<int:badge_assertion_id>/download',
         views.download_badge_assertion_image,
         name="download_badge_assertion_image"),

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # HTMx views
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    path('<int:pk>/create_assertion/hx',
         views.create_badge_assertion_hx,
         name="create_badge_assertion_hx"),

    path('<int:badge_class_id>/assertion/<int:pk>/hx',
         views.badge_assertion_status_hx,
         name="badge_assertion_status_hx"),

]
