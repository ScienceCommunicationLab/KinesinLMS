from django.urls import path
from django.views.generic import TemplateView, RedirectView

from kinesinlms.marketing import views

app_name = "marketing"
urlpatterns = [
    path('', views.index, name='home'),
    path("get_started/", views.get_started, name="get_started"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("newsletter_signup_complete/",
         TemplateView.as_view(template_name="marketing/newsletter_signup_complete.html"),
         name="newsletter_signup_complete"),
    path("honor_code/", views.honor_code, name="honor_code"),
    path("tos/", views.tos, name="tos"),
    path("faq/", views.faq, name="faq"),
    path("testimonials/", views.testimonials, name="testimonials"),
    path("privacy_policy/", views.privacy_policy, name="privacy_policy"),
    path("privacy/", RedirectView.as_view(url='/privacy_policy/')),
    path("trainer-info/", views.trainer_info, name="trainer-info"),
    path("customize_cookies/", views.customize_cookies, name="customize_cookies"),
    # HTMx URLs
    path("hx/speaker", views.speaker_hx, name="speaker_hx"),

    path("hx/toggle_non_essential_cookies",
         views.toggle_non_essential_cookies_hx,
         name="toggle_non_essential_cookies_hx")

]
