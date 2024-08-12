# Course Authoring Overview

KinesinLMS has a simple authoring feature called "Composer." You can use this feature to create a course, add content to it, then make the course visible in the catalog.

Your user is given access to the Composer feature if they have been added to the `AUTHOR` group, or if your user is marked  `staff` or `superuser`.
You'll see a link to "Composer" in the top nav if this is the case.

!!! note
    Remember that the primary way you add a user to a group in Django is to open their
    user in the admin panel and then scroll down to the "Groups" control and add the group there.
    So use this process when you want to add a user to the `AUTHOR` group to give
    them access to Composer.

Composer is still a bit rough, but it should allow you to build up a full course by 1) creating a navigation structure of modules, sections and units, and then 2) adding different types of blocks to each unit.

Currently, the only allowed navigation structure is module / section / unit, but in the future KinesinLMS should support other configurations, such as a two-tiered module / unit stucture.
