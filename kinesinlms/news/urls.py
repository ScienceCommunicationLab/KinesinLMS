from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("", views.NewsPostList.as_view(), name="news-list"),
    path('<slug:slug>/', views.NewsPostDetail.as_view(), name='news-post-detail'),
]
