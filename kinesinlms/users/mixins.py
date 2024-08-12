from django.contrib.auth.mixins import UserPassesTestMixin

from kinesinlms.users.models import GroupTypes
from django.http import HttpRequest


class ComposerAuthorRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        if self.request.user.is_staff:
            return True
        if self.request.user.groups.filter(name=GroupTypes.AUTHOR.name).exists():
            return True
        return False


class SuperuserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class StaffOrSuperuserRequiredMixin(UserPassesTestMixin):
    
    def test_func(self):  # noqa
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or self.request.user.is_staff
        )
