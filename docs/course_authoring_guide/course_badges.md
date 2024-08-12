# Course Badges

You can award a badge to a student who has completed a course. When a student passes a course,
a downloadable badge will appear in their "Progress" tab. If the course awards certificates, the badge will appear next to it.

Before adding a "course passed" badge to a course, you must have already

  1. Created a badge provider. See [Badge Provider Integration](../badges/provider_integration.md)
  2. Set up the badge classes in the remote provider (e.g. Badgr.com). See [Create Badge Classes](../badges/creating_badge_classes.md)
  3. Make sure you have a "course passed" milestone or milestones set for your course. See [Course Milestones](course_milestones.md)

Remember to keep the information from the badges in the remote provider handy, as you'll need to
copy that information into the "add badge class" form.

If you've done all that, you're ready to create a badge class for this course that links to the badge you created in the remote provider.

!!! note
    Currently, KinesinLMS only supports "course passed" type badges, but soon we plan to support assigning badges to any course milestone.

Here's how to do add a "course passed" badge to a course:

  - Open the course in Composer.
  - Go to the "Badges" tab.
  - Click "Add Badge Class" button and in the resulting form add the information copied from the badge class on Badgr.com into the form fields:
    - Copy the badge ID into the "Open badge id" field
    - Copy the external entity ID into the "External entity id" field
    - Copy the image URL into the "Image url" field
    - Fill out the other fields as you see fit ("Name", "slug", etc.)
    - You can also add a description and criteria information on this page. The criteria information will be displayed on the auto-generated
criteria page.
  - Click the "Course Settings" tab
    - Make sure "Enable badges" is checked.

A "course passed" badge is now enabled for your course.
