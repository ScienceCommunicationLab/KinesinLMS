import logging
from typing import List

from django.contrib.auth import get_user_model
from django.forms import Form, ModelChoiceField, CharField, Textarea, BooleanField, HiddenInput

from kinesinlms.catalog.service import do_enrollment
from kinesinlms.course.models import Course, Cohort, CohortMembership
from kinesinlms.course.utils import user_is_enrolled
from kinesinlms.management.models import ManualEnrollment
from kinesinlms.users.models import InviteUser
from kinesinlms.users.services import InviteService

logger = logging.getLogger(__name__)

User = get_user_model()


class ManualEnrollmentForm(Form):
    course = ModelChoiceField(queryset=Course.objects.all(),
                              label="Enroll in Course:",
                              widget=HiddenInput())
    cohort = ModelChoiceField(queryset=Cohort.objects.all(),
                              label="Cohort",
                              required=True)
    invite_unregistered = BooleanField(label="Email invite to unregistered students", required=False)
    students = CharField(widget=Textarea,
                         label="Emails or usernames, one per line (Must use email if inviting unregistered students.)")

    # noinspection PyUnresolvedReferences
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

    def save(self, user) -> ManualEnrollment:
        """
        Creates a series of ManualEnrollment instances for each
        student passed in by form, in the course passed in by the form.
        """

        course = self.cleaned_data['course']
        cohort = self.cleaned_data['cohort']
        invite_unregistered = self.cleaned_data['invite_unregistered']
        student_usernames = self.cleaned_data['students']

        invite_service = None
        if invite_unregistered:
            invite_service = InviteService()

        manual_enrollment = ManualEnrollment.objects.create(course=course,
                                                            cohort=cohort,
                                                            user=user,
                                                            added_student_ids=[],
                                                            skipped_student_ids=[])
        errors = []
        invited_users: List[InviteUser] = []
        for student_username in student_usernames:

            student = None
            if "@" in student_username:
                try:
                    student = User.objects.get(email__iexact=student_username)
                except User.DoesNotExist:
                    if invite_unregistered:
                        try:
                            invite_user = InviteUser.objects.get(email=student_username)
                            errors.append(
                                f"User {student_username} has already been invited (and hasn't registered yet)")
                        except InviteUser.DoesNotExist:
                            invite_user = None
                        if not invite_user:
                            try:
                                invited_user = invite_service.invite_user(student_username, cohort)
                                invited_user.manual_enrollment = manual_enrollment
                                invited_user.save()
                                invited_users.append(invited_user)
                            except Exception as e:
                                errors.append(f"Could not invite user with email {student_username} : {e}")
                    else:
                        errors.append(f"Cannot find user with email: {student_username}")
            else:
                try:
                    student = User.objects.get(username=student_username)
                except User.DoesNotExist:
                    errors.append(f"Cannot find user with username: {student_username}")

            if not student:
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
