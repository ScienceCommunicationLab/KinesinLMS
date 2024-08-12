# Tests

KinesinLMS tries hard to have reasonable suite of tests, and any additional features or updates made should add both unit and end-to-end tests for that feature.

## Test Types

Test are written to use the Pytest library, and include both "unit" tests to exercise individual classes and methods, as well as "integration" or "end-to-end" tests
to excercise a complete workflow as if a user was interacting with the application.

## Env Settings for Tests

Sometimes you'll want slightly different initial configuation values in your environment variables when running tests.
Therefore, we recommend creating a separate .env file specifically for tests, for example `_envs/_local/django_test.env`.

So if you're just starting out, copy the `.env.example` example file to `_envs/_local/django_test.env`, and update it as needed.

There are different ways to load .env files before running tests. KinesinLMS uses the `pytest-dotenv` library, which allows us to add a simple
configuration line to our `.pytest.ini` file indicating where pytest should load env variables before starting.

For example, if you want to use `django_test.env` as your environment file, and you store that file in `_envs/_local/`, you'd set the following in your `.pytest.ini` file:

    env_files = _envs/_local/django_test.env

### Unit Tests

Unit tests are stored in the `/tests` directory of each Django app that composes the KinesinLMS project, e.g. `kinesinlms/badges/tests/`. Pytest will automatically discover
these tests when running.

### Integration Tests

Integration tests are stored in the top-level `/tests` directory of the KinesinLMS project. These tests are a little more
involved, as they rely on the "Selenium" library to start up and drive a browser instance when simulating user interactions.

Integration tests are a little hard to write, but really pay off in turning up issues that unit tests might miss.

In order to run these tests locally you'll need Firefox installed (or choose a different browser to act as the client).

When running the tests on a remote server, you'll need to install `firefox` on the server to run selenium tests.

### Javascript Tests

A few interactive components (e.g. DiagramTool and TableTool) are written in Javascript and/or Typescript and use
npm as a build tool. Therefore, a separate test set up is required to test those components in a granular way.

This is a bit tedious, and as KinesinLMS moves towards using HTMx for interactivity hopefully there will
be less need for these kind of tests, but for now we need to have this separate test structure.

To run this test framework, run:

    npm run test

## Summary for Running Tests

- **Django:** Run Django-focused unit and integration tests by running pytest in the root directory `pytest`.
- **Javascript** Run client-focused javascript tests by running `npm run test`.

### Test Coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    coverage run -m pytest
    coverage html
    open htmlcov/index.html
