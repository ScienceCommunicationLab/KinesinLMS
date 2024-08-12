from django.test import TestCase
from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.composer.factory import SimpleCourseBuilder, CourseBuilderDirector, create_module_node, \
    create_section_node, create_unit_node
from kinesinlms.course.models import Course, CourseNode, CourseUnit
from kinesinlms.course.constants import NodeType, NodePurpose
from kinesinlms.course.tests.factories import CourseFactory
import logging

logger = logging.getLogger(__name__)


class CourseFactoryTestCase(TestCase):

    def setUp(self):
        # Create any necessary test data
        pass

    def test_create_simple_course(self):
        # Use the SimpleCourseBuilder to create a course
        builder = SimpleCourseBuilder()
        director = CourseBuilderDirector(builder)
        course = director.create_course()

        # Check if the necessary model instances are created
        self.assertIsInstance(course, Course)
        self.assertIsInstance(course.catalog_description, CourseCatalogDescription)
        self.assertIsInstance(course.course_root_node, CourseNode)
        self.assertEqual(course.course_root_node.type, NodeType.ROOT.name)

        # Check if the initial nodes are created
        root_node = course.course_root_node
        self.assertEqual(root_node.type, NodeType.ROOT.name)
        module_node = root_node.children.all()[0]
        self.assertEqual(module_node.type, NodeType.MODULE.name)
        section_node = module_node.children.all()[0]
        self.assertEqual(section_node.type, NodeType.SECTION.name)
        unit_node = section_node.children.all()[0]
        self.assertEqual(unit_node.type, NodeType.UNIT.name)

    def test_create_module_section_unit(self):
        # Create a Course instance for testing
        course = CourseFactory.create()

        # Use the helper functions to create a module, section, and unit
        module_node = create_module_node(root_node=course.course_root_node)
        section_node = create_section_node(module_node=module_node)
        unit_node = create_unit_node(
            course=course,
            section_node=section_node,
            slug="test-unit",
            display_name="Test Unit",
            node_purpose=NodePurpose.DEFAULT.name
        )

        # Check if the necessary model instances are created
        self.assertIsInstance(module_node, CourseNode)
        self.assertIsInstance(section_node, CourseNode)
        self.assertIsInstance(unit_node, CourseNode)
        self.assertIsInstance(unit_node.unit, CourseUnit)

