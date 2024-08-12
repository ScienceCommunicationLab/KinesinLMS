# KinesinLMS

KinesinLMS is a simple open-source Learning Management System (LMS) built with the sole developer (or small team) in mind.

It uses Django and tries hard to make it easy for you to understand how things are set up quickly and get the system going
with minimal fuss, while remaining free to extend the app in novel ways. That's the intention, at least.

Key features are:

- **Simple**: "Just enough" LMS to get you started on creating something interesting and engaging. It's not a
  full-featured LMS, but has the basics you'll need as a starting point.
- **Grokkable**: A primary focus of KinesinLMS is to fit entirely inside one developer's head. It tries hard to avoid
  complex frameworks and dependencies, to stick with convention, and to keep the codebase small and understandable.
- **Forgettable**: For those dependencies and infrastructure components that are necessary, KinesinLMS tries to use
  basic, boring, tried-and-true dependencies. Boostrap for styling, only one postgres database, etc. When you forget
  how a dependency or component works, it should be easy to look up and remember.

These docs are an attempt to explain a bit about the architecture of the system, how to set it up and run it, and how to
use some of the tools it provides, such as the course authoring tool "Composer."
