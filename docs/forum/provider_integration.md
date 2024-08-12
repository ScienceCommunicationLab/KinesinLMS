# Forum Provider Setup and Integration

First up, apologies. Setting up and using forums for courses isn't as easy as it should be. Ideally, KinesinLMS
would have its own forum app, and we wouldn't need any of this silliness.

But we don't have that, yet, and we've found Discourse to have the best offering, including an open source
version. So KinesinLMS leans toward using Discourse as a provider of forums.

This means, however, some ugly integration steps.

## Set Up a Production Discourse Server

The first step to providing forum discussions in your KinesinLMS courses is to create an account
on Discourse (easy, but costs money) or set up and configure your own public-facing Discourse instance
from the open source version (difficult, probably still costs money).

Either way, we'll assume you did set up your Discourse forum, and you now have it available at some public URL, for
example, the Discourse forum integrated with SCL's iBiology Courses site is here <https://discuss.ibiology.org>.

We'll now have to configure both this Discourse installation and KinesinLMS so forum access is seamless.

Proceed to ["Connecting Forum"](connecting_to_forum_service.md) for more instructions.
