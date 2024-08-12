# Email Automation Overview

Email automation providers are third-party services that allow you to send an automated email
to one or more of your users, usually when certain events happen (like a student enrolls in a course).

You can configure KinesinLMS to send certain student activity events to your email automation provider. You can then
set up automations in your email automation service to do certain things upon receiving these events, for example,
sending a welcome email to a new student upon receiving an enrollment event, or sending a congratulations email upon
receiving a "course passed" event.

At the moment, KinesinLMS only supports one email automation
provider: [ActiveCampaign](https://www.activecampaign.com/).

But it should be relatively easy to add support for other providers by creating a new implementation of the
`EmailAutomationProvider` base class.

The next section will show you how to set up ActiveCampaign as your email automation provider.
