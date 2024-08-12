# This folder contains the email templates for the survey app.

To create a custom template for a course, create an .html and .txt file
with the same name as the course token and the type of survey (e.g. `BASIC`,
`PRE_COURSE`, `POST_COURSE`, `FOLLOW_UP`).

For example, to create a custom email template for the `PRE_COURSE` survey for the
course with token `ABC_SP`, create the email template files `ABC_SP_PRE_COURSE.html` and
`ABC_SP_PRE_COURSE.txt` in the `survey/email_templates/custom/` subdirectory.

If no custom template exists, the survey app will use the default templates in `survey/emails_templates`
( so don't delete those).
