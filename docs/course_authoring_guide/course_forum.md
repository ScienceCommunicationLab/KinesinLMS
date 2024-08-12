# Course Forum

!!! note
    This section of the docs ... and the forum feature itself... is still in progress. It works at a basic level, but doesn't yet smoothly support multiple cohorts.
    There's some unhappy complexity here due to how we need to configure Discourse cateogies, subcategories and forum topics if we want to limit forum topic discussion by cohort. Apologies.

KinesinLMS relies on an external service to provide a course forum. Currently, the only supported forum is Discourse (a good choice!)
but more may be supported in the future. Using an external forum is good because then we don't have to worry about
implementing and updating forum features.

However, it does mean we have to make sure KinesinLMS integrates correctly with the Discourse forum and knows which
forum categories, subcategories and topics should exist for a course. In a sense, we're wedded to how Discourse arranges things.

The first step to integrating forums into your course is to set up a Discourse server, or purchase an account from Discourse,
and then connect it to KinesinLMS via a Forum Provider. You can read about how do that in the [Forum](../forum/forum_overview.md) section.

Once that's done, you'll need to do two things to include forums in a particular course:

  1. Make sure a forum group, subgroup, category and subcategory exist to match your course and its default cohort.
  2. Add a <code>Forum</code> type block to your course content for each forum topic you want in the course.
will handle creating the forum topic in the remote service.

For step #1, Composer provides a button for configuration if one does not exist:

![Screenshot of the forum tab](/docs/assets/authoring/forum_config.png)

## Configuring the Forum Group

A user group must exist in the remote forum provider to represent students from this course. It should have been created
when you created the course, but if it wasn't, you will see a "Create Group" button. Click it to ask KinesinLMS to create the group in Discourse.

## Configuring the Forum Subgroup

A user group must exist for each cohort in a course. We use these groups to assign cohorts to specific subcategories (see below).

## Configuring the Forum Category

In Discourse, a "Category" is used to group forum topics. KinesinLMS creates one category for each course.
If one doesn't exist, click the "Create Forum Category" button to create one.

## Configuring the Forum Subategory

You may want to limit discussion to students in the same cohort. Ideally, Discourse would allow discussion on any forum topic
to be limited to those in the same cohort as the current student using it. But Discourse doesn't do this :-(

Therefore, to support cohort-limited discussions, KinesinLMS creates a Discourse subcategory for each cohort,
and then creates a complete set of the forum topics in that subcategory. (See [Forum Modesl](../forum/forum_models.md) for more details.)
This is wasteful, as we have to repeat the forum topics for every cohort.

Unfortunately, this approach is the only way in Discourse to limit topic discussions to cohorts. Yes, it's ugly. Alas.

At any rate, every course forum needs *at least* one subcategory for the DEFAULT cohort. Click "Create DEFAULT Cohort Group" if one does not exist.

## Creating a Forum Block

To create a

## Repeating a Forum Topic

You may want to show the same forum topic in multiple units in your course, perhaps to prompt continued discussion with additional questions.
