# Forum Overview

KinesinLMS is designed to integrate with an external forum provider for forum services.

Why not use a local app for forums? There are a number of Django apps that provide forum functionality, but in our
experience none of them are as good as the dedicated forum providers.

Since Discourse was used during KinesinLMS's early development, it is the only forum provider currently supported,
and the data model leans heavily towards supporting Discourse. So a bit of work is probably in order to support
a different forum provider.

## ForumProvider and ForumService

The ForumProvider is an abstract class that defines the properties of our external forum provider. The ForumService
class defines methods to access that provider's functions via an API or webhooks. At the moment, only
one concrete ForumProvider and ForumService is supported (once again, for [Discourse](https://www.discourse.org/)). So the
instructions in this section are specific to Discourse.

It shouldn't be too difficult though if you want to create a new ForumProvider and ForumService for another forum,
such as [Misago](https://misago-project.org/).

Futhermore, you may decide you want the forum to be a part of the KinesinLMS app, and not an external service. If so,
it's probably not a far stretch however if you wanted
to integrate something like [django-machina](https://github.com/ellmetha/django-machina) as an app rather than rely on
an external service.

If you pursue either of these alternatives, let us know how it goes!

## Apologies: Extra Complexity

Discourse has worked really well for us, but it does add some extra complexity to the development process.

Unfortunately, the Discourse site does not have a way to create 'test' accounts, so when developing locally
you'll need to set up a local instance of Discourse...which can be a pain and add complexity that we're
trying hard to avoid. But it's not too bad, especially if you use Docker.

Read on for more info...
