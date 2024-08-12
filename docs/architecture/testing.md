# Testing

Writing tests, ab crunches, broccoli, and mindfulness meditation. All so important. All so very appropriate next week.

KinesinLMS has a basic set of unit and integration tests. Most tests are either unit or integration tests.
Unit tests are based on the Django `TestCase` class and located in each app within the project. Integrations tests
are mostly based on the `StaticLiveServerTestCase` class and located in the top-level tests folder.

All tests are discovered and run when you run `pytest` from the top of the project. Pytest is configured by the
`pytest.ini` file so you can change settings there as you see fit.

It's probably a good idea to always create tests around any updates or changes you make
to the code, and running tests locally and on your remote server when you update your KinesinLMS system.

A few articles to encourage your testing efforts:

- [Testing in Django](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [Testing in Django - Best Practices and Examples](https://realpython.com/testing-in-django-part-1-best-practices-and-examples/)
- [Django Testing Guide](https://atharvashah.netlify.app/posts/tech/django-testing-guide/)
- [Obey the Testing Goat](https://www.obeythetestinggoat.com/)
