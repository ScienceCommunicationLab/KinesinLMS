from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from kinesinlms.users.forms import UserChangeForm, UserCreationForm
from kinesinlms.users.models import InviteUser

User = get_user_model()


@admin.register(InviteUser)
class InviteUserAdmin(admin.ModelAdmin):
    model = InviteUser
    list_display = ('id', 'email', 'cohort', 'manual_enrollment', 'registered_date')


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    fieldsets = (("User", {"fields": (
        "name",
        "is_test_user",
        "informal_name",
        "anon_username",
        "email_automation_provider_user_id",
        "career_stage",
        "gender",
        "gender_description",
        "year_of_birth",
        "why_interested",
        "agree_to_honor_code")}),) + auth_admin.UserAdmin.fieldsets
    list_display = ["id",
                    "username",
                    "anon_username",
                    "name",
                    "email",
                    "email_automation_provider_user_id",
                    "date_joined",
                    "is_superuser",
                    "is_staff",
                    "is_educator",
                    "is_test_user",
                    "year_of_birth",
                    "career_stage",
                    "gender",
                    "gender_description"]
    search_fields = ["name",
                     "anon_username",
                     "email",
                     "username",
                     "email_automation_provider_user_id"]
