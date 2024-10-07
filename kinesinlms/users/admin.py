from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.conf import settings
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from kinesinlms.users.forms import UserAdminChangeForm, UserAdminCreationForm
from kinesinlms.users.models import InviteUser
from django.utils.translation import gettext_lazy as _

User = get_user_model()


if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(InviteUser)
class InviteUserAdmin(admin.ModelAdmin):
    model = InviteUser
    list_display = ("id", "email", "cohort", "manual_enrollment", "registered_date")


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "name", "is_superuser"]
    search_fields = ["name"]
