from django.urls import path

from . import views

app_name = "learning_library"

urlpatterns = [
    path('', views.index, name='index'),
    path('blocks/', views.BlockListView.as_view(), name='blocks'),
    path('course_units/', views.CourseUnitListView.as_view(), name='course_units'),
    path('item-detail/<int:id>/', views.item_detail, name='item_detail'),
]
