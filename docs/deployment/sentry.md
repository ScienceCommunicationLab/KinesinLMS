# Application Monitoring with Sentry

There are a number of services available to help you monitor the state of your system, and warn you
if things are going badly.

Sentry.io is one such service. If you want to use Sentry, and are using Heroku as your service platform, you only need to create a Sentry account, create 
a project in Sentry for your app, note down the "DNS" (client key) for your app, and then set it as an environment variable in Heroku.

For example, if you're configuring a `development` remote for Heroku:

    herok config:set SENTRY_DSN=(your project's DSN in Sentry) --remote development
