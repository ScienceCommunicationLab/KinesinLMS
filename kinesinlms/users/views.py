import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.http import Http404, HttpResponseForbidden
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView
from rest_framework import viewsets, authentication, permissions
from rest_framework.response import Response

from kinesinlms.users.forms import UserSettingsForm
from kinesinlms.users.models import UserSettings
from kinesinlms.users.serializers import UserProfileSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# API VIEWS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UserProfilesViewSet(viewsets.ViewSet):
    """
    Returns user profile data, including 'profile-like'
    properties for each course, e.g. reasonForTaking.

    :return:
    """

    authentication_classes = [authentication.TokenAuthentication, authentication.SessionAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def list(self, request):
        """
        Return engagement data for a course
        """
        queryset = User.objects.filter()
        serializer = UserProfileSerializer(queryset, many=True)
        return Response(serializer.data)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# TEMPLATE VIEWS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# USER SETTINGS
# ~~~~~~~~~~~~~~~~~~~~~


class UserSettingsView(UpdateView):
    """ Provides an editable page for user's settings.

    We know that all user objects have a UserSettings object,
    so no need for a CreateView.

    """
    template_name = 'users/usersettings_detail.html'

    form_class = UserSettingsForm
    model = UserSettings

    def get_queryset(self, *args, **kwargs):
        """
        Allow superuser to see any user settings page.
        Make sure student can only see their own settings page.
        """
        if self.request.user.is_superuser:
            qs = UserSettings.objects.all()
        else:
            qs = UserSettings.objects.filter(user=self.request.user)
        return qs

    def get_object(self, queryset=None):
        user = User.objects.get(id=self.kwargs['pk'])
        user_settings, created = UserSettings.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created new UserSettings for user : {user}")
        return user_settings

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.add_message(self.request, messages.INFO, "Settings saved.")
        return response

    def get_success_url(self) -> str:
        return reverse('users:settings', kwargs={'pk': self.object.user.id})

    def get_context_data(self, **kwargs):
        site_name = Site.objects.get_current().name
        context = super(UserSettingsView, self).get_context_data(**kwargs)
        context["title"] = "My Settings"
        context["section"] = "user_account"
        context["description"] = f"You settings for the {site_name} site."
        return context


# USER DETAIL
# ~~~~~~~~~~~~~~~~~~~~~

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User

    def get_queryset(self):
        """
        Allow superuser to see any detail page.
        Make sure student can only see their own detail page.
        """
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(pk=self.request.user.pk)
        return qs

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        student = self.get_object()
        # Fields to show user in the edit profile screen

        profile_fields = [
            {
                "label": "Name",
                "value": student.name,
            },

            {
                "label": "Informal name",
                "value": student.informal_name,
                "note": "We use your 'informal name' when we send you email."
            },
            {
                "label": "Career stage",
                "value": student.career_stage_name,
            },
            {
                "label": "Gender",
                "value": student.gender_name,
            },
            {
                "label": "Gender description",
                "value": student.gender_description,
            },
            {
                "label": "Year of birth",
                "value": student.year_of_birth,
            },
            {
                "label": "Email",
                "value": student.email,
            }
        ]
        context["title"] = "My Profile"
        context["section"] = "user_account"
        context["description"] = f"The profile information for your user."
        context["profile_fields"] = profile_fields
        return context


user_detail_view = UserDetailView.as_view()


class UserListView(LoginRequiredMixin, ListView):
    model = User

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_staff:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


user_list_view = UserListView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    fields = ["name",
              "informal_name",
              "career_stage",
              "gender",
              "gender_description",
              "year_of_birth"]

    def get_success_url(self) -> str:
        msg = "User profile updated!"
        messages.add_message(self.request, messages.INFO, msg)
        return reverse("users:detail", kwargs={"pk": self.request.user.id})

    def get_object(self, queryset=None):
        return User.objects.get(username=self.request.user.username)

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context['breadcrumbs'] = [
            {
                "url": f"/users/{self.request.user.id}/",
                "label": "My Profile"
            }
        ]
        context["title"] = "Update My Profile"
        context["description"] = "Use this page to update your public profile."
        return context


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.id})


user_redirect_view = UserRedirectView.as_view()
