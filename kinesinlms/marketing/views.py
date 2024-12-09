import datetime
import logging
import random
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.models import Site
from django.core.mail import BadHeaderError, send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.http import require_GET

from config.settings.base import ACCEPT_ANALYTICS_COOKIE_NAME
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.core.utils import get_domain
from kinesinlms.course.models import Course
from kinesinlms.marketing.forms import ContactForm, TrainerInfoForm
from kinesinlms.marketing.models import Testimonial
from kinesinlms.speakers.models import Speaker
from kinesinlms.tracking.event_types import TrackingEventType
from kinesinlms.tracking.tracker import Tracker

logger = logging.getLogger(__name__)


def test_404(request):
    return render(request, "404.html")


@require_GET
def index(request):
    """
    Get a list of course descriptions and send in context for
    the course catalog to render catalog cards.
    """

    if request.user.is_staff or request.user.is_superuser:
        course_descriptions = CourseCatalogDescription.objects.filter()
    else:
        course_descriptions = CourseCatalogDescription.objects.filter(visible=True)

    if request.user.is_authenticated and hasattr(request.user, "enrollments"):
        try:
            # Show 'hidden' courses if user is enrolled in them.
            enrollments = request.user.enrollments.all()
            if enrollments:
                show_course_description_ids = [
                    enrollment.course.catalog_description.id
                    for enrollment in enrollments
                    if enrollment.course.catalog_description
                ]
                extra_course_descriptions = CourseCatalogDescription.objects.filter(
                    visible=False, id__in=show_course_description_ids
                )
                if extra_course_descriptions:
                    course_descriptions = course_descriptions | extra_course_descriptions
        except Exception:
            logger.exception("Could not show hidden and enrolled courses on front page")

    random_speaker = get_random_speaker()

    context = {"course_descriptions": course_descriptions, "random_speaker": random_speaker}

    return render(request, "marketing/home.html", context)


@require_GET
def honor_code(request):
    context = {"title": "Honor Code", "description": "The honor code that guides your work on KinesinLMS."}
    return render(request, "marketing/honor_code.html", context)


@require_GET
def tos(request):
    context = {
        "title": "Terms of Service",
        "description": "The terms of service you agree to when using KinesinLMS website.",
    }
    return render(request, "marketing/tos.html", context)


@require_GET
def faq(request):
    context = {
        "title": "Frequently Asked Questions",
        "description": "Some answers to questions you might have about our site...",
    }
    return render(request, "marketing/faq.html", context)


@require_GET
def testimonials(request):
    site_testimonials = Testimonial.objects.filter(visible=True, course=None).all()
    courses_w_testimonials = Course.objects.filter(testimonials__isnull=False).distinct()

    context = {
        "title": "Testimonials",
        "description": "Testimonials from our students",
        "site_testimonials": site_testimonials,
        "courses": courses_w_testimonials,
    }

    return render(request, "marketing/testimonials.html", context)


@require_GET
def customize_cookies(request):
    action = request.GET.get("action", "").upper()

    context = {
        "hide_accept_cookie_banner": True,
        "title": "Customize Cookies",
        "description": "Set your cookie preferences.",
    }

    if action in ["ACCEPT", "REJECT"]:
        # Set cookie and redirect to page
        # so cookie state is picked up in template
        # and correct message and buttons are displayed.
        redirect_url = reverse("marketing:customize_cookies")
        response = redirect(redirect_url)
        if action == "ACCEPT":
            accept_analytics_cookies(response)
        elif action == "REJECT":
            reject_analytics_cookies(request, response)
        return response

    return render(request, "marketing/customize_cookies.html", context)


@require_GET
def privacy_policy(request):
    context = {"title": "Privacy Policy", "description": "The privacy policy for the KinesinLMS website."}
    return render(request, "marketing/privacy_policy.html", context)


@require_GET
def get_started(request):
    site_name = Site.objects.get_current().name
    context = {"title": "Get Started", "description": f"How to get started using {site_name}."}
    return render(request, "marketing/get_started.html", context)


@require_GET
def about(request):
    site_name = Site.objects.get_current().name
    context = {"title": "About", "description": f"A bit about {site_name}."}
    return render(request, "marketing/about.html", context)


def contact(request):
    if request.method == "POST" and request.user.is_authenticated:
        form = ContactForm(request.POST)
        if form.is_valid():
            # Send email to the team
            try:
                username = request.user.username
                email = request.user.email
                message = form.cleaned_data["message"]

                email_body = (
                    f"Username : {username} \n"
                    f"Email: {email}\n\n"
                    f"Environment: {settings.DJANGO_PIPELINE} \n"
                    f"Message:\n---------------------------------\n"
                    f"{message}\n\n\n\n---------------------------------\n\n"
                )
                send_mail(
                    "Contact form submission from kinesinlms.org",
                    email_body,
                    "no-response@kinesinlms.org",
                    ["courses@kinesinlms.org", "admin@kinesinlms.org"],
                )
            except Exception:
                logger.exception(
                    f"Could not email contact form submission: "
                    f"request.POST: {request.POST} "
                    f"request.user: {request.user}"
                )
            form = None
    else:
        form = ContactForm()

    context = {"form": form, "title": "Contact Us", "description": "Contact the team at KinesinLMS."}
    return render(request, "marketing/contact.html", context)


def trainer_info(request):
    if request.method == "POST":
        form = TrainerInfoForm(request.POST)
        if form.is_valid():
            # TODO: Send request to Lambda or directly to ActiveCampaign
            try:
                message = (
                    "Someone submitted the form indicating they're interested "
                    "in requiring KinesinLMS for their trainees.\n\n "
                    "Details :\n-----------------------------------\n\n"
                )
                message += "Full name: {} \n".format(form.cleaned_data["full_name"])
                message += "Email: {} \n".format(form.cleaned_data["email"])
                message += "Courses: {} \n".format(form.cleaned_data["courses"])
                message += "Job title: {} \n".format(form.cleaned_data["job_title"])
                message += "Description: {} \n\n".format(form.cleaned_data["description"])
                send_mail(
                    "Inquiry: requiring courses for trainees",
                    message,
                    "courses@kinesinlms.org",
                    ["admin@kinesinlms.org"],
                )
                try:
                    Tracker.track(
                        event_type=TrackingEventType.ADMIN_KINESINLMS_TRAINER_FORM_SUBMITTED.value,
                        user=request.user,
                        event_data=form.cleaned_data,
                    )
                except Exception as e:
                    # fail silently
                    logger.exception("Couldn't record KINESINLMS_TRAINER_FORM activity to tracker. {}".format(e))
                return render(request, "marketing/trainer_info_thanks.html")
            except BadHeaderError:
                messages.error(
                    request, message="Couldn't process form. Please contact courses@kinesinlms.org directly."
                )
                return render(request, "marketing/trainer_info.html", {"form": form})
        else:
            messages.error(request, message="Invalid form. Please try again.")
            form = TrainerInfoForm()
    else:
        form = TrainerInfoForm()

    return render(request, "marketing/trainer_info.html", {"form": form})


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMx views
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def speaker_hx(request):
    """
    Return another YouTube video of our speakers.
    """

    previous_speaker_id = request.GET.get("previous", None)
    speaker = get_random_speaker(current_speaker_id=previous_speaker_id)

    context = {"block_speaker": speaker}
    return render(request, "marketing/hx/speaker_video.html", context)


def toggle_non_essential_cookies_hx(request):
    """
    Set state to indicate the user has accepted non-essential cookies.
    """

    action = request.GET.get("action", "REJECT").upper()
    if action not in ["ACCEPT", "REJECT"]:
        action = "REJECT"

    control = request.GET.get("control", "accept_cookie_banner")
    if control == "accept_cookie_banner":
        template = "includes/hx/accept_cookie_banner.html"
    else:
        raise ValueError(f"Invalid control: {control}")

    context = {}
    if control == "accept_cookie_banner":
        context["hide_accept_cookie_banner"] = True

    # Get response so we can set cookies
    response = HttpResponse()
    if action == "ACCEPT":
        accept_analytics_cookies(response)
    else:
        reject_analytics_cookies(request, response)

    # ...then render template, which expects cookie
    # operations to already be done.
    response.content = loader.render_to_string(template, context, request)

    return response


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Helper functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def get_random_speaker(current_speaker_id=None) -> Optional[Speaker]:
    speakers = Speaker.objects.filter(video_url__isnull=False).exclude(video_url="")
    if current_speaker_id:
        speakers = speakers.filter(~Q(id=current_speaker_id))
    speaker_ids = speakers.values_list("id", flat=True)
    if not speaker_ids:
        return None
    speaker_id = random.choice(list(speaker_ids))
    speaker = Speaker.objects.get(id=speaker_id)
    return speaker


def accept_analytics_cookies(response):
    days_expire = 365
    max_age = days_expire * 24 * 60 * 60
    expire_time = now() + datetime.timedelta(days=days_expire)
    expires = datetime.datetime.strftime(expire_time, "%a, %d-%b-%Y %H:%M:%S GMT")
    domain = get_domain()
    response.set_cookie(
        ACCEPT_ANALYTICS_COOKIE_NAME,
        "ACCEPT",
        max_age=max_age,
        expires=expires,
        domain=domain,
        samesite="Lax",
    )
    logger.debug(f"set cookie {ACCEPT_ANALYTICS_COOKIE_NAME} to ACCEPT")


def reject_analytics_cookies(request, response):
    days_expire = 365
    max_age = days_expire * 24 * 60 * 60
    expire_time = now() + datetime.timedelta(days=days_expire)
    expires = datetime.datetime.strftime(expire_time, "%a, %d-%b-%Y %H:%M:%S GMT")
    domain = get_domain()
    response.set_cookie(
        ACCEPT_ANALYTICS_COOKIE_NAME, "REJECT", max_age=max_age, expires=expires, domain=domain, samesite="Lax"
    )

    # Cleanup by deleting GA cookies from browser
    # Domain must be exact, and google puts a period before the domain
    domain_with_starting_period = f".{domain}"
    for cookie_name in request.COOKIES.keys():
        logger.info(f"Checking cookie: {cookie_name}")
        if cookie_name.startswith("_ga") or cookie_name.startswith("_gid") or cookie_name.startswith("_gat"):
            # Delete cookie was only working for _ga cookie, not _ga_blahblah.
            # So trying to delete by setting expire to now.
            response.set_cookie(cookie_name, domain=domain_with_starting_period, value="", max_age=0)
            logger.info(f"Setting cookie {cookie_name} domain {domain_with_starting_period} to expire now")

            # logger.info(f"Deleting cookie: {cookie_name} domain {google_domain}")
            # response.delete_cookie(cookie_name, domain=google_domain)

    # No cleanup for ActiveCampaign since it doesn't set cookies.
    # We just won't add the javascript tracker library now that
    # the user has rejected cookies.
