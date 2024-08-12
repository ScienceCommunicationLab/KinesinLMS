import django_filters
from kinesinlms.users.models import User


class UserFilter(django_filters.FilterSet):
    informal_name = django_filters.CharFilter(
        field_name="informal_name", label="Informal Name"
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "name",
            "informal_name",
        ]
