from django.urls import path

from . import views

app_name = "badges"
urlpatterns = [

    path('', views.help_main_page, name="main"),

    path('<slug:help_page_slug>/',
         views.help_page,
         name="help_page"),

]
