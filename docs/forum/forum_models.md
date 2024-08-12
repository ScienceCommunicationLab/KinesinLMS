Modeling the Form Provider
=======================================

This section describes how the objects provided in Discourse are modeled and modified in KinsekinLMS,
and how we access their representations in Discourse via the Discourse API.

Modeling Discourse Objects
-----------------------------

To support forum discussions, Discourse provides "Topics" that are composed of a post and a number of replies.
So whenever we have a discussion point in a course, we create a topic in Discourse.

Discourse allows topics to be grouped into categories, so the first inclination would be to just
put all topics for a course into a category, and then we're done.

However, when one wants to limit some topics to a particular cohort in a course, things get a bit more complicated.

Discourse allows categories to be grouped into parent categories, so the solution we came up with was
to make a category for each course and then a subcategory for each cohort in the course. Then, a copy
of each topic is placed in that subcategory. (Background
discussion [here](https://meta.discourse.org/t/how-to-structure-discourse-for-an-online-course/152572/11))

In KinesinLMS, each course gets a DEFAULT cohort when it is created. And most courses only have
that DEFAULT cohort, so this is not a big deal -- there will be one parent category in Discouse and one
subcategory for the Discourse cohort.

But if a course has multiple cohorts, then each cohort will need to have its own subcategory and a copy of
each topic.

This is a bit of a hack, but it works. And it allows us to use the Discourse API when a course is authored
to create the category, subcategories and topics, and then when a course is run to create a subcategory and
copy the topics for any new cohort created in the course.

Discourse API
-----------------------------

The Discourse API is a bit odd: sometimes it wants an ID, sometimes a name, and sometimes a slug.

So in our models you'll often see two identifiers saved for a Discourse object: an ID and a name or an ID and a slug
(depending on the model type). We then use one or the other in a particular API call.


Discourse Groups
-----------------------------

Whenever we set up Discourse to host topics for a course, we first start by creating "groups" in Discourse
into which we can add students as they enroll.

Each course will get at least two Discourse groups:

- one group for all topics *any* enrolled student in this course can view.
- one group for each specific cohort in the course.

For the 'cohort' group, we always add a Discourse group for the course's DEFAULT cohort. We then
add a new group any time an author or admin adds a new cohort to the course.

We follow a standard naming convention when creating a Discourse group for a cohort: [course token]_co_[cohort name].

For example if you have a course with a token of DEMO_SP, then the Discourse group for the DEFAULT cohort
will be named DEMO_SP_co_DEFAULT.

Any other cohorts added to an KinesinLMS course should automatically get a new Discourse group created in Discourse
and assigned to it through the CohortForumGroup model in Django.


Django Models
-----------------

The ForumTopic model is the main Django model to represent a topic in a course, and thereby in Discourse.
This model is linked directly a Block of type FORUM_TOPIC. It stores the Discourse ID and Discourse slug for
a topic (different Discourse endpoints use one or the other).

Each time a FORUM_TOPIC block type is added to a course, KinesinLMS will need to use the Discourse API to create
a new topic in Discourse for every subcategory in the course's main Discourse category.

And every time a new cohort is added to a course, KinesinLMS will need to use the Discourse API to create new
topics for every FORUM_TOPIC block in a course, creating them in the new cohort's corresponding Discourse subcategory.

Unlike the Assessment model, ForumTopic *is not* in a one-to-one relationship with Block. This is because
we need one ForumTopic instance for each Topic instance created in Discourse. And since we have to duplicate
topics for every cohort (as explained above), we need a ForumTopic instance for every cohort.

The ForumTopic model also has a many-to-one relationship with ForumSubcategory, to represent how these topics
are grouped into the subcagegory in Discourse.

The ForumSubcategory can be thought of as a "proxy" for the Discourse subcategory. It's type property defines
whether it's a COHORT subcategory or an ALL_ENROLLED subcategory. It then has a foreign key to a
CohortForumGroup (if it's a COHORT type) or a CourseForumGroup (if it's an ALL_ENROLLED type) to represent
which group is allowed to view the topics in this subcategory.

To limit users in Discourse to the correct topics, a Discourse group must be created for a course, and then
an additional group for each cohort in the course. The CourseForumGroup and CohortForumGroup models represent
these groups in KinesinLMS.

If there is no need to segment topics by cohort, then there will only be one 'default' ForumSubcategory and one
'default' CohortForumGroup for a course. The `is_default` property for CohortForumGroup would be set to True.
All cohorts for the course would then use the same default CohortForumGroup.

A cohort in a course is linked to CohortForumGroup via the Cohort model's `cohort_forum_group` foreign key property. 
This allows many cohorts in a course to use the same CohortForumGroup, such as in the scenario described above.
