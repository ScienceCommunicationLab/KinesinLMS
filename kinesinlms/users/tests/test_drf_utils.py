import pytest
from rest_framework.reverse import reverse

from kinesinlms.users.models import User

pytestmark = pytest.mark.django_db


def test_user_detail(user: User):
    user_detail_url = reverse("user-detail", kwargs={"pk": user.pk})
    assert user_detail_url == f"/api/users/{user.pk}/"


def test_user_list():
    assert reverse("user-list") == "/api/users/"


def test_user_me():
    assert reverse("user-me") == "/api/users/me/"
