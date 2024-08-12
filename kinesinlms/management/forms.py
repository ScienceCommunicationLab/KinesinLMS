import logging
from typing import List

from waffle.models import Switch

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.forms import Form, ModelChoiceField, CharField, Textarea, BooleanField, ModelForm
from django.utils.translation import gettext as _

from kinesinlms.badges.models import BadgeClass
from kinesinlms.catalog.service import do_enrollment, do_unenrollment
from kinesinlms.core.models import SiteProfile
from kinesinlms.course.models import Course, Enrollment, Cohort, CohortMembership
from kinesinlms.course.utils import user_is_enrolled
from kinesinlms.management.models import ManualEnrollment, ManualUnenrollment

logger = logging.getLogger(__name__)

User = get_user_model()


class SiteFeaturesForm(Form):
    """
    Form that exposes the various Waffle Switches we use
    to toggle certain site features on and off.
    """

    # We're manually adding which fields we want the user to be
    # able to manage via the management panel (rather than just
    # rendering all Switch and Flag objects in the database).
    LEARNING_LIBRARY = BooleanField(required=False)
    COMPOSER = BooleanField(required=False)
    TESTIMONIALS = BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for switch in Switch.objects.all():
            if switch.name in self.fields:
                self.fields[switch.name].initial = switch.active
    

class SiteProfileForm(ModelForm):
    name = CharField(label="Site Name", required=True)

    class Meta:
        model = SiteProfile
        fields = [
            'name',
            'facebook_url',
            'twitter_username',
            'support_email',
            'newsletter_signup_url',
            'educators_newsletter_signup_url'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].initial = Site.objects.get_current().name

    def save(self, commit=True):
        site_profile = super().save(commit=False)
        site = Site.objects.get_current()
        site.name = self.cleaned_data['name']
        site.save()
        site_profile.site = site
        if commit:
            site_profile.save()
        return site_profile


class ManualUnenrollmentForm(Form):
    course = ModelChoiceField(queryset=Course.objects.all(), label="Unenroll from Course:")
    students = CharField(widget=Textarea, label="Emails or usernames, one per line (do not use commas).")

    def clean_students(self) -> List[str]:
        """
        Remove duplicates.

        Returns:
            List of unique student names.
        """
        logger.debug(f"Validating students...")
        data = self.cleaned_data['students']

        students_data = data.split("\n")
        # Use set to ignore duplicate student identifiers.
        student_usernames = set()
        for student_token in students_data:
            student_token = student_token.strip()
            student_usernames.add(student_token)
        student_usernames = list(student_usernames)
        return student_usernames

    def do_unenrollments(self, user) -> ManualUnenrollment:
        """
        Tries to unenroll each student
        """

        course = self.cleaned_data['course']
        student_usernames = self.cleaned_data['students']

        manual_unenrollment = ManualUnenrollment.objects.create(course=course,
                                                                user=user,
                                                                unenrolled_student_ids=[],
                                                                skipped_student_ids=[])
        errors = []
        for student_username in student_usernames:

            if "@" in student_username:
                try:
                    student = User.objects.get(email__iexact=student_username)
                except User.DoesNotExist:
                    errors.append(f"Cannot find user with email: {student_username}")
                    continue
            else:
                try:
                    student = User.objects.get(username=student_username)
                except User.DoesNotExist:
                    errors.append(f"Cannot find user with username: {student_username}")
                    continue

            if user_is_enrolled(user=student, course=course):
                try:
                    enrollment: Enrollment = do_unenrollment(user=student, course=course)
                    assert enrollment.active == False, "Enrolment was not set to inactive"
                    manual_unenrollment.unenrolled_student_ids.append(student.id)
                    logger.info(f"Enrollment {enrollment} is now inactive. "
                                f"unenrolled user : {student} in course {course}")
                except Exception as e:
                    manual_unenrollment.skipped_student_ids.append(student.id)
                    errors.append(f"Error unenrolling student {student} : {e}")
            else:
                manual_unenrollment.skipped_student_ids.append(student.id)

        if errors:
            manual_unenrollment.errors = errors

        manual_unenrollment.save()

        return manual_unenrollment


class ManualEnrollmentForm(Form):
    course = ModelChoiceField(queryset=Course.objects.all(),
                              label="Enroll in Course:",
                              required=True)
    cohort = ModelChoiceField(queryset=Cohort.objects.all(),
                              label="Cohort",
                              required=True)
    invite_unregistered = BooleanField(label="Email invite to unregistered students", required=False)
    students = CharField(widget=Textarea,
                         label="Emails or usernames, one per line (Must use email if inviting unregistered students.)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        course = None
        if self.data:
            course_id = self.data.get('course', None)
            if course_id:
                course = Course.objects.get(id=course_id)
        else:
            initial = kwargs['initial']
            course = initial.get('course', None)

        if course:
            self.fields['cohort'].queryset = course.cohorts.all()
            self.fields['cohort'].disabled = False
            self.fields['cohort'].empty_label = None
        else:
            self.fields['cohort'].queryset = Cohort.objects.all()
            self.fields['cohort'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def clean_students(self) -> List[str]:
        """
        Remove duplicates.

        Returns:
            List of unique student names.
        """
        logger.debug(f"Validating students...")
        data = self.cleaned_data['students']

        students_data = data.split("\n")

        # Use set to ignore duplicate student identifiers.
        student_usernames = set()

        for student_token in students_data:
            student_token = student_token.strip()
            student_usernames.add(student_token)

        student_usernames = list(student_usernames)

        return student_usernames

    def create_enrollments(self, user) -> ManualEnrollment:
        """
        Creates a series of ManualEnrollment instances for each
        student passed in by form, in the course passed in by the form.
        """

        course = self.cleaned_data['course']
        cohort = self.cleaned_data['cohort']
        student_usernames = self.cleaned_data['students']

        manual_enrollment = ManualEnrollment.objects.create(course=course,
                                                            cohort=cohort,
                                                            user=user,
                                                            added_student_ids=[],
                                                            skipped_student_ids=[])
        errors = []
        for student_username in student_usernames:

            if "@" in student_username:
                try:
                    student = User.objects.get(email__iexact=student_username)
                except User.DoesNotExist:
                    errors.append(f"Cannot find user with email: {student_username}")
                    continue
            else:
                try:
                    student = User.objects.get(username=student_username)
                except User.DoesNotExist:
                    errors.append(f"Cannot find user with username: {student_username}")
                    continue

            if user_is_enrolled(user=student, course=course):
                cohort_membership = CohortMembership.objects.get(cohort__course=course, student=student)
                if cohort_membership.cohort != cohort:
                    # Need to move already enrolled user to new cohort
                    manual_enrollment.moved_from_cohort_ids.append(student.id)
                    cohort_membership.cohort = cohort
                    cohort_membership.save()
                else:
                    manual_enrollment.skipped_student_ids.append(student.id)
            else:
                try:
                    enrollment = do_enrollment(user=student, course=course, cohort=cohort)
                    manual_enrollment.added_student_ids.append(student.id)
                    logger.info(f"Badge enroll {enrollment}: enrolled user : {student} in course {course}")
                except Exception as e:
                    manual_enrollment.skipped_student_ids.append(student.id)
                    errors.append(f"Error enrolling student {student} : {e}")

        if errors:
            manual_enrollment.errors = errors

        manual_enrollment.save()

        return manual_enrollment


class UpdateCourseForm(ModelForm):
    class Meta:
        model = Course
        fields = [
            'enable_forum',
            'enable_email_automations',
            'enable_badges',
            'enable_surveys'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        site = Site.objects.get_current()
        forum_provider_defined = hasattr(site, "forum_provider")
        if not forum_provider_defined:
            self.fields['enable_forum'].disabled = True
            self.fields['enable_forum'].help_text = "Forum provider not defined in site settings."
        email_automations_provider_defined = hasattr(site, "email_automation_provider")
        if not email_automations_provider_defined:
            self.fields['enable_email_automations'].disabled = True
            self.fields['enable_email_automations'].help_text = "Email automations provider not defined in site settings."


class DeleteCourseForm(Form):
    delete_blocks = BooleanField(required=False,
                                 label=_("Delete related Blocks"),
                                 help_text=_("If selected, the system will delete all blocks used in the course. Note "
                                             "the delete will fail if other courses are using any of the blocks."))


class DuplicateCourseForm(ModelForm):
    duplicate_blocks = BooleanField(required=False,
                                    label=_("Duplicate content blocks"),
                                    help_text=_("If selected, the system will duplicate each "
                                                "content block used in this course. Otherwise, only "
                                                "meta-data and navigation structures are duplicated (actual "
                                                "content will be shared between the old and new course)."))

    class Meta:
        model = Course
        fields = ['slug',
                  'run',
                  'self_paced',
                  'duplicate_blocks']


class CourseBadgeClassForm(ModelForm):
    class Meta:
        model = BadgeClass
        fields = [
            'slug',
            'type',
            'name',
            'provider',
            'external_entity_id'
        ]
