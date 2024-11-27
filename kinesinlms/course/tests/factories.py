import logging
import random
from datetime import timedelta

import factory  # noqa
from django.utils.timezone import now
from factory import post_generation  # noqa

from kinesinlms.assessments.tests.factories import LongFormAssessmentFactory
from kinesinlms.badges.models import BadgeProvider, BadgeProviderType
from kinesinlms.badges.tests.factories import BadgeClassFactory, BadgeProviderFactory
from kinesinlms.catalog.tests.factories import CourseCatalogDescriptionFactory
from kinesinlms.certificates.models import CertificateTemplate, Signatory
from kinesinlms.course.constants import CourseUnitType, MilestoneType, NodeType
from kinesinlms.course.models import (
    Block,
    Cohort,
    Course,
    CourseNode,
    CourseStaff,
    CourseUnit,
    Enrollment,
    EnrollmentSurvey,
    EnrollmentSurveyQuestion,
    EnrollmentSurveyQuestionType,
    Milestone,
)
from kinesinlms.learning_library.constants import BlockType, ResourceType
from kinesinlms.learning_library.models import BlockResource, Resource, UnitBlock
from kinesinlms.marketing.tests.factories import TestimonialFactory
from kinesinlms.sits.models import SimpleInteractiveToolType
from kinesinlms.sits.tests.factories import SimpleInteractiveToolFactory

logger = logging.getLogger(__name__)


class SignatoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Signatory
        django_get_or_create = ("slug",)

    name = "Some Signatory Name"
    title = "Some Signatory Title"
    slug = "some-signatory"
    organization = "Some Signatory Organization"


class CertificateTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CertificateTemplate
        django_get_or_create = (
            "course",
        )  # Specify the field(s) to use for get_or_create

    description = "A description for some certificate template."
    custom_template_name = None

    @post_generation
    def post(self: CertificateTemplate, create, extracted, **kwargs):  # noqa: F841
        """
        Add a signatory to the certificate template.
        """
        signatory_1 = SignatoryFactory()
        self.signatories.add(signatory_1)


class BlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Block


class ResourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Resource

    resource_file = factory.django.FileField(filename="test_file.rst")


class BlockResourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockResource

    resource = factory.SubFactory(ResourceFactory)


class CourseUnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseUnit
        django_get_or_create = (
            "slug",
        )  # Specify the field(s) to use for get_or_create


class CourseNodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourseNode

    release_datetime = None


class MilestoneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Milestone
        django_get_or_create = ("course", "slug")

    slug = "one_assessment_to_pass"
    description = "Answer one assessments to pass course"
    type = MilestoneType.CORRECT_ANSWERS.name
    count_requirement = 1
    required_to_pass = True
    badge_class = factory.SubFactory(BadgeClassFactory)


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment
        django_get_or_create = ("student", "course")

    active = True


class TimedCourseFactory(factory.django.DjangoModelFactory):
    """
    Same as CourseFactory, except that it creates
    the third module with a release date in the future.
    """

    class Meta:
        model = Course
        django_get_or_create = ("slug", "run")

    catalog_description = factory.SubFactory(CourseCatalogDescriptionFactory)
    course_root_node = factory.SubFactory(CourseNodeFactory, release_datetime=now())

    slug = "TEST"  # Some Course !
    run = "R1"
    display_name = "Test Course"
    advertised_start_date = now().strftime("%B %d, %Y")
    self_paced = False
    enable_certificates = True
    enable_badges = True

    # Dates
    start_date = now()
    end_date = now() + timedelta(days=100)
    enrollment_start_date = now() + timedelta(days=-10)
    enrollment_end_date = now() + timedelta(days=+10)
    days_early_for_beta = 100

    @post_generation
    def post(self, create, extracted, **kwargs):
        badge_class = BadgeClassFactory.create(
            course=self,
        )

        # Can't get RelatedModel to work do doing the milestone
        # creation manually here.
        milestone = MilestoneFactory.create(
            course=self,
            name="Test Course Passed Milestone",
            badge_class=badge_class,
            count_requirement=1,
            required_to_pass=True,
        )
        logger.debug(f"Created milestone {milestone} for course {self}")

        # Build a simple course structure in MPTT and attach units to them.
        # This is kind of involved but probably still better than using fixtures
        # or some other mechanism to build up a course before running tests....at least I tell myself that.

        module_1 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Basic Stuff",
            display_sequence=1,
            slug="module_1",
        )
        section_1 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_1,
            content_index=1,
            display_sequence=1,
            display_name="Basic Lesson 1",
            slug="section_1",
        )
        section_2 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_1,
            content_index=2,
            display_sequence=2,
            display_name="Basic Lesson 2",
            slug="section_2",
        )

        module_2 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Intermediate Stuff",
            display_sequence=2,
            slug="module_2",
        )
        section_3 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_2,
            content_index=1,
            display_sequence=1,
            display_name="Intermediate Lesson 3",
            slug="section_3",
        )
        section_4 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_2,
            content_index=2,
            display_sequence=2,
            display_name="Intermediate Lesson 4",
            slug="section_4",
        )

        module_3 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Advanced Stuff",
            display_sequence=3,
            slug="module_3",
            release_datetime=now() + timedelta(days=10),
        )
        section_5 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_3,
            content_index=1,
            display_sequence=1,
            display_name="Advanced Lesson 5",
            slug="section_5",
        )
        section_6 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_3,
            content_index=2,
            display_sequence=2,
            display_name="Advanced Lesson 6",
            slug="section_6",
        )

        # Create some basic content for each section
        # Put two units in every section.
        section_nodes = [
            section_1,
            section_2,
            section_3,
            section_4,
            section_5,
            section_6,
        ]
        units_per_section = 2
        unit_id = 1
        for section_node in section_nodes:
            for unit_count in range(1, units_per_section + 1):
                # Create some fake content for each unit: some html, a video and an assessment.

                course_unit = CourseUnitFactory(
                    type=CourseUnitType.STANDARD.name,
                    slug=f"course_unit_{unit_id}",
                    course=self,
                )

                # ADD VIDEO CONTENT....
                video_block = BlockFactory(
                    slug=f"video_for_unit_{unit_id}",
                    display_name=f"Video for Unit {unit_id}",
                    type=BlockType.VIDEO.name,
                    json_content={
                        "video_id": "wf9QrrRzJys",
                        "header": "Some video header for course_unit_1 "
                        "(Using 'How to use this website' and placeholder video).",
                    },
                )
                transcript_resource = ResourceFactory.create(
                    type=ResourceType.VIDEO_TRANSCRIPT.name
                )
                video_block.resources.add(transcript_resource)
                video_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=video_block, block_order=1
                )
                logger.debug(f"Created video_block {video_block} for course {self}")
                logger.debug(
                    f"Created video_unit_block {video_unit_block} for course {self}"
                )

                # ADD HTML CONTENT....
                html_block = BlockFactory(
                    type=BlockType.HTML_CONTENT.name,
                    html_content=f"<h1>Test Unit {unit_id}</h1>"
                    f"<p>This is a simple HTML block for "
                    f"unit {unit_id}.</p>",
                )
                html_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=html_block, block_order=2
                )
                logger.debug(f"Created html_block {html_block} for course {self}")
                logger.debug(
                    f"Created html_unit_block {html_unit_block} for course {self}"
                )

                # ADD ASSESSMENT CONTENT...
                assessment_block = BlockFactory(type=BlockType.ASSESSMENT.name)
                assessment = LongFormAssessmentFactory(block=assessment_block)
                assessment_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=assessment_block, block_order=3
                )
                assessment_block.slug = f"block-{assessment.slug}"
                assessment_block.save()
                logger.debug(f"Created assessment {assessment} for course {self}")
                logger.debug(
                    f"Created assessment_unit_block {assessment_unit_block} for course {self}"
                )

                # ADD DIAGRAM CONTENT...
                diagram_block = BlockFactory(
                    type=BlockType.SIMPLE_INTERACTIVE_TOOL.name
                )
                SimpleInteractiveToolFactory(
                    block=diagram_block,
                    tool_type=SimpleInteractiveToolType.DIAGRAM.name,
                )
                UnitBlock.objects.create(
                    course_unit=course_unit, block=diagram_block, block_order=4
                )

                # ATTACH UNIT TO NODES
                unit_node = CourseNodeFactory(
                    type=NodeType.UNIT.name,
                    parent=section_node,
                    display_name=f"Course Unit {unit_id}",
                    unit=course_unit,
                    display_sequence=unit_id,
                    slug=f"course_unit_{unit_id}",
                )
                logger.debug(f"Created unit_node {unit_node} for course {self}")

                unit_id += 1


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course
        django_get_or_create = ("slug", "run")

    catalog_description = factory.SubFactory(CourseCatalogDescriptionFactory)
    course_root_node = factory.SubFactory(CourseNodeFactory)

    slug = "TEST"
    run = "SP"
    display_name = "Test Course (Self-Paced)"
    short_name = "Test Course (SP)"
    advertised_start_date = now().strftime("%B %d, %Y")
    self_paced = True
    enable_certificates = True
    enable_badges = True

    # Dates
    start_date = now()
    end_date = None
    enrollment_start_date = now() + timedelta(days=-10)
    enrollment_end_date = None
    days_early_for_beta = 100

    @post_generation
    def post(self, create, extracted, **kwargs):
        if not create:
            return

        # Add some tags
        self.tags.add("tag1", "tag2", "tag3")

        CertificateTemplateFactory.create(
            course=self,
        )

        try:
            provider = BadgeProvider.objects.get(type=BadgeProviderType.BADGR.name)
        except BadgeProvider.DoesNotExist:
            provider = BadgeProviderFactory.create(
                type=BadgeProviderType.BADGR.name,
            )
        badge_class = BadgeClassFactory.create(
            provider=provider,
            course=self,
        )

        # Create and add three Testimonial instances.
        for _ in range(3):
            testimonial = TestimonialFactory.create()
            testimonial.course = self
            testimonial.quote = (
                f"Testimonial {random.randint(1, 100)} + {testimonial.quote}"
            )
            testimonial.save()
            self.testimonials.add(testimonial)

        # Can't get RelatedModel to work so doing the milestone
        # creation manually here.
        MilestoneFactory.create(
            course=self,
            name="Test Course Passed Milestone",
            badge_class=badge_class,
            count_requirement=1,
            required_to_pass=True,
        )

        # Build a simple course structure in MPTT and attach units to them.
        # This is kind of involved but probably still better than using fixtures
        # or some other mechanism to build up a course before running tests....at least I tell myself that.

        module_1 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Basic Stuff",
            display_sequence=1,
            slug="basic_module",
        )
        module_2 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Advanced Stuff",
            display_sequence=2,
            slug="advanced_module",
        )

        section_1 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_1,
            content_index=1,
            display_sequence=1,
            display_name="Basic Lesson 1",
            slug="basic_section_1",
        )
        section_2 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_1,
            content_index=2,
            display_sequence=2,
            display_name="Basic Lesson 2",
            slug="basic_section_2",
        )

        section_3 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_2,
            content_index=3,
            display_sequence=3,
            display_name="Advanced Lesson 3",
            slug="advanced_section_3",
        )

        # Create some basic content for each section
        # Put two units in every section.
        unit_id = 1
        for section_node in [section_1, section_2, section_3]:
            units_per_section = 2
            for unit_count in range(1, units_per_section + 1):
                logger.debug(f"Creating test unit id # {unit_id}")

                # Create some fake content for each unit: some html, a video and an assessment.
                course_unit = CourseUnitFactory(
                    type=CourseUnitType.STANDARD.name,
                    slug=f"course_unit_{unit_id}",
                    course=self,
                )

                # ADD VIDEO CONTENT....
                video_block = BlockFactory(
                    slug=f"video_for_unit_{unit_id}",
                    display_name=f"Video for Unit {unit_id}",
                    type=BlockType.VIDEO.name,
                    json_content={
                        "video_id": "wf9QrrRzJys",
                        "header": "Some video header for course_unit_1 "
                        "(Using How to Use This Website and placeholder video).",
                    },
                )
                logger.debug(f"Created video_block {video_block} for course {self}")

                transcript_resource = ResourceFactory.create(
                    type=ResourceType.VIDEO_TRANSCRIPT.name
                )
                video_block.resources.add(transcript_resource)
                video_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=video_block, block_order=1
                )
                logger.debug(
                    f"Created video_unit_block {video_unit_block} for course {self}"
                )

                # ADD HTML CONTENT....
                html_block = BlockFactory(
                    type=BlockType.HTML_CONTENT.name,
                    html_content=f"<h1>Test Unit {unit_id}</h1>"
                    f"<p>This is a simple HTML block for "
                    f"unit {unit_id}.</p>",
                )
                logger.debug(f"Created html_block {html_block} for course {self}")
                html_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=html_block, block_order=2
                )
                logger.debug(
                    f"Created html_unit_block {html_unit_block} for course {self}"
                )

                # ADD ASSESSMENT CONTENT...
                assessment_block = BlockFactory(type=BlockType.ASSESSMENT.name)
                assessment = LongFormAssessmentFactory(block=assessment_block)
                logger.debug(f"Created assessment {assessment} for course {self}")
                assessment_unit_block = UnitBlock.objects.create(
                    course_unit=course_unit, block=assessment_block, block_order=3
                )
                logger.debug(
                    f"Created assessment_unit_block {assessment_unit_block} for course {self}"
                )

                # ADD DIAGRAM CONTENT...
                diagram_block = BlockFactory(
                    type=BlockType.SIMPLE_INTERACTIVE_TOOL.name
                )
                SimpleInteractiveToolFactory(
                    block=diagram_block,
                    tool_type=SimpleInteractiveToolType.DIAGRAM.name,
                )
                UnitBlock.objects.create(
                    course_unit=course_unit, block=diagram_block, block_order=4
                )

                # ATTACH UNIT TO NODES
                unit_node = CourseNodeFactory(
                    type=NodeType.UNIT.name,
                    parent=section_node,
                    display_name=f"Course Unit {unit_id}",
                    unit=course_unit,
                    display_sequence=unit_id,
                    slug=f"course_unit_{unit_id}",
                )
                logger.debug(f"Created unit_node {unit_node} for course {self}")

                unit_id += 1


class CohortFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cohort


class CourseWithRepeatedBlockFactory(factory.django.DjangoModelFactory):
    """
    This factory creates a test course that has an Assessment block repeated
    in the course in read-only mode.
    """

    class Meta:
        model = Course
        django_get_or_create = ("slug", "run")

    catalog_description = factory.SubFactory(CourseCatalogDescriptionFactory)
    course_root_node = factory.SubFactory(CourseNodeFactory)

    slug = "TEST_REPEATED_BLOCK"
    run = "SP"
    display_name = "Test Course With Repeated Block (Self-Paced)"
    short_name = "Test Course (SP)"
    advertised_start_date = now().strftime("%B %d, %Y")
    self_paced = True
    enable_certificates = True
    enable_badges = True

    # Dates
    start_date = now()
    end_date = None
    enrollment_start_date = now() + timedelta(days=-10)
    enrollment_end_date = None
    days_early_for_beta = 100

    @post_generation
    def post(self, create, extracted, **kwargs):
        badge_class = BadgeClassFactory.create(
            course=self,
        )

        # Can't get RelatedModel to work do doing the milestone
        # creation manually here.
        milestone = MilestoneFactory.create(
            course=self,
            name="Test Course Passed Milestone",
            badge_class=badge_class,
            count_requirement=1,
            required_to_pass=True,
        )
        logger.debug(f"Created milestone {milestone} for course.")

        # Build a simple course structure in MPTT and attach units to them.
        # This is kind of involved but probably still better than using fixtures
        # or some other mechanism to build up a course before running tests....at least I tell myself that.

        module_1 = CourseNodeFactory(
            type=NodeType.MODULE.name,
            parent=self.course_root_node,
            display_name="Basic Stuff",
            display_sequence=1,
            slug="basic_module",
        )
        section_1 = CourseNodeFactory(
            type=NodeType.SECTION.name,
            parent=module_1,
            content_index=1,
            display_sequence=1,
            display_name="Basic Lesson 1",
            slug="basic_section_1",
        )

        # Create a unit with an assessment
        course_unit_1 = CourseUnitFactory(
            type=CourseUnitType.STANDARD.name, slug="course_unit_1", course=self
        )
        assessment_block = BlockFactory(type=BlockType.ASSESSMENT.name)
        LongFormAssessmentFactory(block=assessment_block)
        UnitBlock.objects.create(
            course_unit=course_unit_1, block=assessment_block, block_order=1
        )

        CourseNodeFactory(
            type=NodeType.UNIT.name,
            parent=section_1,
            display_name="Course Unit 1",
            unit=course_unit_1,
            display_sequence=1,
            slug="course_unit_1",
        )

        # Create a unit that repeats same assessment in read-only form
        course_unit_2 = CourseUnitFactory(
            type=CourseUnitType.STANDARD.name, slug="course_unit_2", course=self
        )
        UnitBlock.objects.create(
            course_unit=course_unit_2,
            block=assessment_block,
            read_only=True,
            block_order=2,
        )

        CourseNodeFactory(
            type=NodeType.UNIT.name,
            parent=section_1,
            display_name="Course Unit 2",
            unit=course_unit_2,
            display_sequence=2,
            slug="course_unit_2",
        )


class CourseStaffFactory(factory.django.DjangoModelFactory):
    """
    Factory for testing CourseStaff model.
    """

    class Meta:
        model = CourseStaff


class EnrollmentSurveyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EnrollmentSurvey


class EnrollmentSurveyQuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EnrollmentSurveyQuestion

    created_at = now()
    updated_at = now()
    question_type = EnrollmentSurveyQuestionType.MULTIPLE_CHOICE.name
    question = "Why are you enrolling in this course?"
    definition = [
        {
            "key": "educator",
            "value": "I am an educator reviewing this content, or using it in teaching",
        },
        {
            "key": "independent-learner",
            "value": "I am a learner taking this course independently for my own education",
        },
        {
            "key": "required",
            "value": "I am a learner taking this course to fulfill a course or program requirement",
        },
        {"key": "other", "value": "( other )"},
    ]
