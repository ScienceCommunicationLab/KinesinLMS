import logging
from typing import List

from kinesinlms.course.models import CourseUnit
from kinesinlms.learning_library.constants import BlockType

logger = logging.getLogger(__name__)


def get_course_module_resources(course) -> List:
    course_modules = []

    # Iterate through each CourseUnit and pick out resources
    for module_node in course.course_root_node.children.all():
        resource_items = []
        num_assessments = 0
        num_discussion_topics = 0
        assessments = []
        forum_topics = []
        worksheets = []

        for section_node in module_node.children.all():
            for unit_node in section_node.children.all():
                course_unit: CourseUnit = unit_node.unit
                for block in course_unit.contents.all():
                    if block.type == BlockType.ASSESSMENT.name:
                        assessments.append(
                            {
                                "display_name": block.display_name,
                                "question": block.assessment.question,
                            }
                        )
                    elif block.type == BlockType.FORUM_TOPIC.name:
                        display_name = block.discussion_topic_title
                        if not display_name:
                            display_name = block.display_name
                        forum_topics.append(
                            {
                                "display_name": display_name,
                                "html_content": block.html_content,
                            }
                        )
                    elif block.type == BlockType.VIDEO.name:
                        transcript_resource_id = None
                        for block_resource in block.resources.all():
                            if block_resource.type == "VIDEO_TRANSCRIPT":
                                transcript_resource_id = block_resource.id
                        resource_items.append(
                            {
                                "type": BlockType.VIDEO.name.lower(),
                                "title": block.display_name,
                                "video_header": block.video_header,
                                "url": f"https://www.youtube.com/watch?v={block.video_id}",
                                "transcript_resource_id": transcript_resource_id,
                            }
                        )

        course_module = {
            "slug": module_node.slug,
            "module_id": module_node.id,
            "content_index": module_node.content_index,
            "display_name": module_node.display_name,
            "resource_items": resource_items,
            "num_assessments": num_assessments,
            "num_discussion_topics": num_discussion_topics,
            "forum_topics": forum_topics,
            "assessments": assessments,
            "worksheets": worksheets,
        }
        course_modules.append(course_module)

    return course_modules
