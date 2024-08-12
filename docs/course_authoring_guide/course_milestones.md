# Course Milestones

In any course you can define various "milestones" a student can achieve. They can be simply informational (e.g. "you watched all videos in the course"), or
they can be required to pass a course.

By allowing more than one milestone to be required for passing a course, Composer gives you the ability to make more interesting criteria than
simply answering a certain number of assessments. This allows you to create requirements like "you have to watch five videos, post twice to the forum, and answer 10 assessments correctly to pass this course."

All milestones are shown to the student on the "Progress" tab when they're viewing the course. On that screen, they're grouped for the student into required and non-required tables.

To modify the milestones, click the "Milestones" tab when editing a course in Composer.

Below are descriptions of each of the fields you can configure for a milesone.

## Required to Pass

If checked, this milestone is required for a student to pass a course. Other milestones may also be checked.

## Type

You must define the type of milestone. It can be one of the following:

   - "Correct Answers" : Counts the number of correct answers to assessments
   - "Video Plays" : Counts the number of times a video is played (Distinct. Only counts plays for each video once...following plays of the same video are ignored).
   - "Forum Posts" : Counts the number of forum posts by a student in this course.
   - "Simple Interactive Tool (SIT) Integrations" : Counts the number of times a student interacts with SITs in the course (Distinct. Only counts interations with each SIT once...following interactions with the same SIT are ignored.)

## Slug

You can define a slug for this milestone. If you don't provide one, Composer will. But you might want to give it a useful name, as the slug will be used
in things like events that you might look at later. Defining a useful name now might make that task easier.

## Name

A name for the milestone. This is shown to the student in the "Progress" tab.

## Description

A longer description of the milestone. This is shown to the student in the "Progress" tab.

## Count Requirement

Defines the number of required interactions. The nature of the count depends on the type defined above, e.g. clicking play is a count for a "Video Plays" type, answering an assessment correctly is a count for a "Correct Answers" type.

## Count graded only

This only applies if the milestone is type "Correct answers". When you add an assessment to a course, it can be defined as "graded" or "not graded." So enabling this option means only "graded" assessments will be counted.

## Minimum total score to reach milestone

This only applies if the milestone is type "Correct answers". An assessment can be assigned a score (the default is "1"). Those scores are summed and measured against this value if it's defined.

## Badge Class

The author can link a badge class to this metric so that the student receives a badge once the milestone is reached. (This feature is in development.)

Note that this badge would only be for the current milestone...defining a "course passed" badge is a separate badge defined in the "Badges" section. See the [badges](../badges/badges_overview.md) page for more information.
