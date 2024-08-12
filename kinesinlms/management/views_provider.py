import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.sites.models import Site
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    DeleteView,
    UpdateView,
)
from django.utils.translation import gettext as _

import config.settings.base
from kinesinlms.badges.forms import BadgeProviderForm
from kinesinlms.badges.models import BadgeProvider
from kinesinlms.email_automation.forms import EmailAutomationProviderForm
from kinesinlms.email_automation.models import EmailAutomationProvider
from kinesinlms.email_automation.service import EmailAutomationService
from kinesinlms.email_automation.utils import get_email_automation_service
from kinesinlms.external_tools.forms import ExternalToolProviderForm
from kinesinlms.external_tools.models import ExternalToolProvider
from kinesinlms.forum.forms import ForumProviderForm
from kinesinlms.forum.models import ForumProvider
from kinesinlms.survey.forms import SurveyProviderForm
from kinesinlms.survey.models import SurveyProvider
from kinesinlms.users.mixins import SuperuserRequiredMixin

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SERVICE MANAGEMENT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Views for managing the service providers for the site.


# EXTERNAL TOOL PROVIDER
# ................................................................


class ExternalToolProviderListView(SuperuserRequiredMixin, ListView):
    model = ExternalToolProvider
    template_name = "management/provider/external_tool/external_tool_provider_list.html"
    context_object_name = "external_tool_providers"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": _("Management"), "url": reverse("management:index")}
            ],
            "section": "management",
            "title": _("External Tool Providers"),
            "description": _("Manage external tool providers."),
        }
        context.update(extra_context)
        return context


class ExternalToolProviderDetailView(SuperuserRequiredMixin, DetailView):
    model = ExternalToolProvider
    template_name = (
        "management/provider/external_tool/external_tool_provider_detail.html"
    )
    context_object_name = "external_tool_provider"


class ExternalToolProviderCreateView(SuperuserRequiredMixin, CreateView):
    model = ExternalToolProvider
    template_name = (
        "management/provider/external_tool/external_tool_provider_create.html"
    )
    context_object_name = "external_tool_provider"
    form_class = ExternalToolProviderForm
    success_url = reverse_lazy("management:external_tool_provider_list")

    def form_valid(self, form):
        messages.success(
            self.request, _("External tool provider created successfully.")
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": _("Management"), "url": reverse("management:index")},
                {
                    "label": _("External Tool Providers"),
                    "url": reverse("management:external_tool_provider_list"),
                },
            ],
            "section": "management",
            "title": _("Create External Tool Provider"),
            "description": _("Create a new external tool provider"),
        }
        context.update(extra_context)
        return context


class ExternalToolProviderUpdateView(SuperuserRequiredMixin, UpdateView):
    model = ExternalToolProvider
    template_name = (
        "management/provider/external_tool/external_tool_provider_update.html"
    )
    context_object_name = "external_tool_provider"
    form_class = ExternalToolProviderForm
    success_url = reverse_lazy("management:external_tool_provider_list")

    def form_valid(self, form):
        messages.success(
            self.request, _("External tool provider updated successfully.")
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": _("Management"), "url": reverse("management:index")},
                {
                    "label": _("External Tool Providers"),
                    "url": reverse("management:external_tool_provider_list"),
                },
            ],
            "section": "management",
            "title": _("Edit External Tool Provider"),
            "description": _("Edit an exising external tool provider"),
        }
        context.update(extra_context)
        return context


class ExternalToolProviderDeleteView(SuperuserRequiredMixin, DeleteView):
    model = ExternalToolProvider
    template_name = (
        "management/provider/external_tool/external_tool_provider_confirm_delete.html"
    )
    success_url = reverse_lazy("management:external_tool_provider_list")
    context_object_name = "external_tool"

    def get_success_url(self):
        messages.success(self.request, "External tool provider deleted successfully.")
        return super().get_success_url()


# SURVEY PROVIDER
# ................................................................


class SurveyProviderListView(SuperuserRequiredMixin, ListView):
    model = SurveyProvider
    template_name = "management/provider/survey/survey_provider_list.html"
    context_object_name = "survey_providers"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": "Management", "url": reverse("management:index")}
            ],
            "section": "management",
            "title": "Survey Providers",
            "description": "Manage survey providers.",
        }
        context.update(extra_context)
        return context


class SurveyProviderDetailView(SuperuserRequiredMixin, DetailView):
    model = SurveyProvider
    template_name = "management/provider/survey/survey_provider_detail.html"
    context_object_name = "survey_provider"


class SurveyProviderCreateView(SuperuserRequiredMixin, CreateView):
    model = SurveyProvider
    template_name = "management/provider/survey/survey_provider_create.html"
    context_object_name = "survey_provider"
    form_class = SurveyProviderForm
    success_url = reverse_lazy("management:survey_provider_list")

    def form_valid(self, form):
        messages.success(self.request, _("Survey provider created successfully."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": _("Management"), "url": reverse("management:index")},
                {
                    "label": "Survey Providers",
                    "url": reverse("management:survey_provider_list"),
                },
            ],
            "section": "management",
            "title": _("Create Survey Provider"),
            "description": _("Create a new survey provider"),
            "survey_provider_api_key_exists": settings.SURVEY_PROVIDER_API_KEY
            is not None,
        }
        context.update(extra_context)
        return context


class SurveyProviderUpdateView(SuperuserRequiredMixin, UpdateView):
    model = SurveyProvider
    template_name = "management/provider/survey/survey_provider_update.html"
    context_object_name = "survey_provider"
    form_class = SurveyProviderForm
    success_url = reverse_lazy("management:survey_provider_list")

    def form_valid(self, form):
        messages.success(self.request, _("Survey provider updated successfully."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extra_context = {
            "breadcrumbs": [
                {"label": _("Management"), "url": reverse("management:index")},
                {
                    "label": _("Survey Providers"),
                    "url": reverse("management:survey_provider_list"),
                },
            ],
            "section": "management",
            "title": _("Edit Survey Provider"),
            "description": _("Edit an exising survey provider"),
            "survey_provider_api_key_exists": settings.SURVEY_PROVIDER_API_KEY
            is not None,
        }
        context.update(extra_context)
        return context


class SurveyProviderDeleteView(SuperuserRequiredMixin, DeleteView):
    model = SurveyProvider
    template_name = "management/provider/survey/survey_provider_confirm_delete.html"
    success_url = reverse_lazy("management:survey_provider_list")
    context_object_name = "survey_provider"

    def get_success_url(self):
        messages.success(self.request, _("Survey provider deleted successfully."))
        return super().get_success_url()

    def form_valid(self, form):
        if self.object.surveys.exists():
            err_message = _(
                "Cannot delete this survey provider. One or more Surveys exist that use it. "
                "Please update these surveys to use a different Survey Provider, or delete them, "
                "before deleting this survey provider"
            )
            messages.error(self.request, err_message)
            return redirect("management:foundation_provider_list")
        return super().form_valid(form)


# FORUM PROVIDER
# ................................................................


@user_passes_test(lambda u: u.is_superuser)
def forum_provider(request):
    site = Site.objects.get_current()
    provider, created = ForumProvider.objects.get_or_create(site=site)
    if request.method == "POST":
        form = ForumProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.SUCCESS, _("Saved forum provider settings.")
            )
            return redirect("management:forum_provider")
        else:
            messages.add_message(
                request, messages.ERROR, _("Error saving forum provider settings.")
            )
    else:
        form = ForumProviderForm(instance=provider)
    context = {
        "breadcrumbs": [{"label": "Management", "url": reverse("management:index")}],
        "section": "management",
        "title": _("Forum Provider"),
        "description": _("Manage the forum provider."),
        "fluid_info_bar": True,
        "form": form,
        "api_key_exists": provider.api_key is not None,
        "sso_secret_exists": provider.sso_secret is not None,
    }
    return render(request, "management/provider/forum/forum_provider.html", context)


# Email Automation Provider
# ................................................................


@user_passes_test(lambda u: u.is_superuser)
def email_automation_provider(request):
    site = Site.objects.get_current()
    provider, created = EmailAutomationProvider.objects.get_or_create(site=site)
    if request.method == "POST":
        form = EmailAutomationProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Saved email automation provider settings."),
            )
            return redirect("management:email_automation_provider")
        else:
            messages.add_message(
                request,
                messages.ERROR,
                _("Error saving email automation provider settings."),
            )
    else:
        form = EmailAutomationProviderForm(instance=provider)

    if config.settings.base.EMAIL_AUTOMATION_PROVIDER_API_KEY:
        key_snippet = settings.EMAIL_AUTOMATION_PROVIDER_API_KEY[:3] + "..."
    else:
        key_snippet = None

    test_api_htmx_url = reverse("management:email_automation_provider_test_api_hx")

    context = {
        "section": "management",
        "title": _("Email Automation Provider"),
        "breadcrumbs": [{"label": _("Management"), "url": reverse("management:index")}],
        "form": form,
        "api_credentials_exist": provider.api_key is not None
        and provider.api_url is not None,
        "api_key_exists": provider.api_key is not None,
        "description": _("Manage the email automation provider."),
        "key_snippet": key_snippet,
        "fluid_info_bar": True,
        "test_api_htmx_url": test_api_htmx_url,
    }
    return render(
        request,
        "management/provider/email_automation/email_automation_provider.html",
        context,
    )


# Badge Provider
# ................................................................


@user_passes_test(lambda u: u.is_superuser)
def badge_provider(request):
    site = Site.objects.get_current()
    provider, created = BadgeProvider.objects.get_or_create(site=site)
    if request.method == "POST":
        form = BadgeProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.SUCCESS, _("Saved badge provider settings.")
            )
            return redirect("management:badge_provider")
        else:
            messages.add_message(
                request, messages.ERROR, _("Error saving badge provider settings.")
            )
    else:
        form = BadgeProviderForm(instance=provider)
    context = {
        "section": "management",
        "title": _("Badge Provider"),
        "breadcrumbs": [{"label": _("Management"), "url": reverse("management:index")}],
        "form": form,
        "description": _("Manage the badge provider."),
        "fluid_info_bar": True,
    }
    return render(request, "management/provider/badge/badge_provider.html", context)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# HTMX VIEW METHODS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def email_automation_provider_test_api_hx(request):
    """
    Test the connection to the Email Automation Provider API.
    """
    
    error_msg = None
    try:
        service: EmailAutomationService = get_email_automation_service()
        can_connect: bool = service.test_api_connection()
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error testing Email Automation Provider API connection: {error_msg}")
        can_connect = False

    api_connect_results = {
        "can_connect": can_connect,
        "error": error_msg,
    }

    test_api_htmx_url = reverse("management:email_automation_provider_test_api_hx")

    context = {
        "api_credentials_exist": settings.EMAIL_AUTOMATION_PROVIDER_API_KEY is not None,
        "api_connect_results": api_connect_results,
        "test_api_htmx_url": test_api_htmx_url,
    }
    return render(request, "management/provider/hx/test_api_connection.html", context)
