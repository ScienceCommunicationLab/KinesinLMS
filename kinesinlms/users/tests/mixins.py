from kinesinlms.users.tests.factories import UserFactory


class StaffOnlyTestMixin:
    """
    Mix in to a view test to ensure the defined `url` is only accessible to staff users.
    """

    def setUp(self):
        super().setUp() # noqa

        if not hasattr(self, 'student'):
            self.student = UserFactory()

        if not hasattr(self, 'staff'):
            self.staff = UserFactory(is_staff=True)

    def test_student_view(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        # Redirect (to login) or permission denied are acceptable
        self.assertIn(response.status_code, [403, 302])  # noqa

    def test_staff_view(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)  # noqa


class SuperuserOnlyTestMixin(StaffOnlyTestMixin):
    """
    Mix in to a view test to ensure the defined `url` is only accessible to superusers.
    """

    def setUp(self):
        super().setUp()

        if not hasattr(self, 'superuser'):
            self.superuser = UserFactory(is_staff=True, is_superuser=True)

    def test_staff_view(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        # Redirect (to login) or permission denied are acceptable
        self.assertIn(response.status_code, [302, 403])  # noqa

    def test_superuser_view(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)  # noqa
