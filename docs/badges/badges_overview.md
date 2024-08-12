# Badges Overview

"Open Badges" are digital images (usually .png or .svg format) that encode accomplishments in a standardized format.
Information about the accomplishment that earned that badge, including who earned it and the criteria involved,
is cryptographically signed and embedded in the image.

Using cryptography to encode this information allows the badge to be verified as
authentic and to be shared reliably across the web. Badges can be displayed on social media, in email,
on websites, and in digital portfolios. They can also be collected and displayed in a "backpack"
or "passport" system, such as Badgr.com, Mozilla Backpack, or Open Badge Passport.

The open badges architecture is governed by a published, evolving standard, currently
at [version 2.1](https://www.imsglobal.org/spec/ob/v2p1/).

The use of badges as a reward system in online courses has been shown to encourage user interaction with courses and
improve course completion rates.

KinesinLMS provides a "BadgeProvider" class to define a third-party badge provider. At the moment,
the only provider supported is Badgr.com.

To award badges for things like course completion, you'll need to:

 - create an account on Badgr.com
 - create an "issuer" for your organization
 - create one or more "badge clasess" under that issuer for the different badges you want to award.

You then set up a BadgeProvider instance in KinesinLMS to represent the issuer.

After than, you set up a BadgeClass instance in KinesinLMS for every badge class you created in Badgr, and associate
that BadgeClass instance with a course and milestone (e.g. if a student reaches the "course passed" milestone for a course, they get a badge.)

At the moment, KinesinLMS only supports awarding badges for course completion. However, the architecture is
designed to be extensible, so it should be possible to add support for other types of badges in the future.

More resources on Open Badges:

- [What are Open Badges](https://community.canvaslms.com/t5/Canvas-Badges/What-are-Open-Badges/ta-p/528726)
- [Getting Started with Open Badges and Open Microcredentials](https://files.eric.ed.gov/fulltext/EJ1240709.pdf)
- [Open Badges](https://openspace.etf.europa.eu/pages/open-badges)
