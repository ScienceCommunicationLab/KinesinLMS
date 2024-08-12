import abc
import logging

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.course.constants import NodeType, NodePurpose
from kinesinlms.course.models import CourseNode, CourseUnit, Course
from kinesinlms.course.tests.factories import CourseUnitFactory, CourseNodeFactory

logger = logging.getLogger(__name__)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Course Builders
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~


class BaseCourseBuilder(abc.ABC):
    """
    Base builder for a course. This class defines the steps necessary to
    create a course and related model instances.
    """

    def _create_course_instance(self, **kwargs):
        logger.debug("  - Creating a new course instance...")
        course: Course = Course.objects.create(**kwargs)
        self.course = course

    def _create_catalog_description(self, course: Course):  # noqa: F841
        logger.debug("  - Adding initial catalog description...")
        self.course.catalog_description = CourseCatalogDescription.objects.create()
        self.course.save()

    def _add_initial_nodes(self):
        logger.debug("  - Adding initial nodes...")
        self.course.course_root_node = CourseNode.objects.create(type=NodeType.ROOT.name)
        self.course.save()

    def create_course(self, **kwargs) -> Course:
        logger.debug("Creating a new course...")
        self._create_course_instance(**kwargs)
        self._create_catalog_description(course=self.course)
        self._add_initial_nodes()
        return self.course


class SimpleCourseBuilder(BaseCourseBuilder):
    """
    Simple builder for a course. This class defines the steps necessary to
    create a course and related model instances.
    Right now this is the only really valid builder we have for
    creating a course.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create_course(self, **kwargs):
        super().create_course(**kwargs)

    def _add_initial_nodes(self):
        super()._add_initial_nodes()
        # Add a default Module, section, and unit node
        module_node = create_module_node(root_node=self.course.course_root_node)
        section_node = create_section_node(module_node=module_node)
        create_unit_node(course=self.course,
                         section_node=section_node,
                         slug="new-unit",
                         display_name="New Unit",
                         node_purpose=NodePurpose.DEFAULT.name,
                         autocreate_course_unit=True)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Course Builder Directory
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CourseBuilderDirector(object):
    """
    Manages building a new course.
    """

    def __init__(self, builder: BaseCourseBuilder):
        if not builder:
            raise ValueError("builder parameter must be defined.")
        self._builder = builder

    def create_course(self, **kwargs) -> Course:
        self._builder.create_course(**kwargs)
        return self._builder.course


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Utility methods
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_module_node(root_node: CourseNode, content_index=1) -> CourseNode:
    """
    Create a new MODULE node and add to end of MODULE node's SECTION list.
    """

    # Set up any initial defaults
    if root_node.children:
        display_sequence = root_node.children.count()
    else:
        display_sequence = 0

    module_node = CourseNodeFactory.create(parent=root_node,
                                           slug="new-module",
                                           display_name="New Module",
                                           type=NodeType.MODULE.name,
                                           display_sequence=display_sequence,
                                           content_index=content_index)
    return module_node


def create_section_node(module_node: CourseNode, content_index=1) -> CourseNode:
    """
    Create a new SECTION node and add to end of MODULE node's SECTION list.
    """

    # Set up any initial defaults
    if module_node.children:
        display_sequence = module_node.children.count()
    else:
        display_sequence = 0

    section_node = CourseNodeFactory.create(parent=module_node,
                                            slug="new-section",
                                            display_name="New Section",
                                            type=NodeType.SECTION.name,
                                            display_sequence=display_sequence,
                                            content_index=content_index)

    return section_node


def create_unit_node(course: Course,
                     section_node: CourseNode,
                     slug: str = None,
                     display_name: str = None,
                     node_purpose: str = NodePurpose.DEFAULT.name,
                     course_unit: CourseUnit = None,
                     autocreate_course_unit: bool = True,
                     content_index=1) -> CourseNode:
    """
    Creates a new "UNIT" CourseNode as a child of the section_node
    argument. The new node is added to the end of the child node list.

    Adds and attaches a CourseUnit to this new UnitNode if
    the create_course_unit boolean argument is True.

    Args:
            course:                     Course this unit is being added to.
            section_node:               CourseNode parent to add new CourseNode to
                                        as a child node
            slug:                       Slug for the new UNIT CourseNode
            display_name:               Display name for the new UNIT CourseNode
            course_unit:                If a course_unit argument is provided, use this
                                        instance for the unit field on the new CourseNode.
            node_purpose:               Default setting for node_purpose.
            autocreate_course_unit:     Boolean flag indicating whether to auto create
                                        a new CourseUnit if one isn't provided.
            content_index:

    """

    # Validate args...
    if not section_node:
        raise ValueError("section_node parameter must be defined.")
    if not slug:
        slug = "new-unit"

    try:
        NodePurpose[node_purpose]
    except Exception:
        raise ValueError("Invalid node_purpose.")

    # Create CourseUnit if necessary...
    if not course_unit and autocreate_course_unit:
        course_unit = CourseUnitFactory.create(course=course,
                                               slug='new-course-unit')

    # Set up any initial defaults
    if section_node.children:
        display_sequence = section_node.children.count()
    else:
        display_sequence = 0

    # Create ...
    unit_node = CourseNodeFactory.create(parent=section_node,
                                         slug=slug,
                                         purpose=node_purpose,
                                         display_name=display_name,
                                         type=NodeType.UNIT.name,
                                         display_sequence=display_sequence,
                                         content_index=content_index,
                                         unit=course_unit)

    return unit_node
