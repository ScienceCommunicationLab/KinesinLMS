# Guiding Principles

"Whaa? Another LMS? There's
already [a thousand out there](https://elearningindustry.com/directory/software-categories/learning-management-systems)!
Why one more?"

Yes, it's true. There are quite a few e-Learning systems a team can pick from. However, if you filter that list for
certain
features, licenses and programming languages, it drops to a much smaller list very quickly.

Let's say you want a platform

1. with a strong open-source license like AGPL
2. ...and developed with Python and Django
3. ...and focused on minimizing complexity so your small development team (probably one person) can manage the entire
   project and add the interesting features you need quickly.

Now that list is looking much smaller. And if you add in the requirement that the platform be designed to support
e-Learning
research projects, it's even more limited.

We built KinesinLMS because we wanted a platform that met those criteria. We wanted a platform that was
designed to be quickly and easily set up by small teams doing interesting e-learning research projects.

What follows is a rough collection of the ideas and principles that guide KinesinLMS's development.

## Keep Things Simple

- If there's a simple way to do something, do it that way even if it's not as snazzy.
- (But go ahead and be snazzy if it provides real user experience and learning benefit.)
- Try hard to keep developer workflows simple, especially building and publishing. Limit the number of
  points where things can go wrong.

## Keep Code Understandable

- **Good style:** follow the Google Python Style guidelines.
- **Simple style:** don't use fancy features of the language if a simpler feature will do. Channel your inner Strunk and
  White.
- **Code comments:** when you wade into the debate on whether to include more or less comments with a block of code, err
  on the side the being obvious rather than being cryptically terse.

## Respect User Privacy

- By default, don't use third-party tracking services.
- Internal tracking should use anonymous identifiers as much as possible.
- It should be easy for an admin to remove a user from a system. It might not be possible to completely remove every
  trace of activity (e.g. event logs), it should be possible to easily delete those things we can delete and for the
  rest remove all identifying information.
