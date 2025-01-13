import json
import logging
import os
import re
import zipfile
from typing import Dict, List, Optional

import requests
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from kinesinlms.catalog.models import CourseCatalogDescription
from kinesinlms.composer.import_export.importer import CourseImporterBase, ImportStatus
from kinesinlms.composer.import_export.kinesinlms.constants import (
    KinesinLMSCourseExportFormatID,
)
from kinesinlms.composer.import_export.model import CourseImportOptions
from kinesinlms.composer.models import CourseMetaConfig
from kinesinlms.course.constants import NodeType
from kinesinlms.course.models import Course, CourseNode, CourseResource
from kinesinlms.course.serializers import (
    CourseNodeSerializer,
    CourseUnitSerializer,
    IBiologyCoursesCourseSerializer,
)
from kinesinlms.forum.utils import get_forum_service
from kinesinlms.learning_library.constants import BlockType, ResourceType
from kinesinlms.learning_library.models import Resource
from kinesinlms.survey.models import Survey, SurveyType

logger = logging.getLogger(__name__)


class IBiologyCoursesCourseImporter(CourseImporterBase):
    """
    Import legacy export format from iBiology Courses into the Kinesin LMS.

    We do this in a two-step process:
    1.      We use the IBiologyCoursesCourseSerializer to create the top-level
            Course and CourseCatalogDescription instances.
    2.      We use methods defined in this class to create the CourseNode tree
            and related CourseUnit and Block instances.

    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PUBLIC METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def import_course_from_json(
        self,
        course_json: Dict,
        course_slug: str = None,
        course_run: str = None,
        display_name: str = None,
        options: CourseImportOptions = None,  # noqa: F841
    ) -> Course:
        """
        Load a Course from JSON. Override the slug, run or display name if provided in arguments.

        Args:
            course_json:
            course_slug:
            course_run:
            display_name:
            options:            CourseImportOptions instance with options for import.

        Returns:
            Course instance

        """

        if not course_json:
            raise Exception("Course json is empty!")

        # course_json could either be the full export format,
        # which includes 'metadata' and 'course' dictionaries,
        # or just the 'course' dictionary.
        document_type = course_json.get("document_type", None)
        if document_type != KinesinLMSCourseExportFormatID.IBIO_COURSES_FORMAT.value:
            raise Exception(f"Invalid document type: {document_type}")

        metadata = {}
        if "metadata" in course_json:
            metadata = course_json.get("metadata", {})
        else:
            document_type = None
        if "course" in course_json:
            course_json = course_json["course"]

        if not course_slug:
            course_slug = course_json.get("slug", None)
        else:
            # override course slug in json
            course_json["slug"] = course_slug

        if not course_run:
            course_run = course_json.get("run", None)
        else:
            course_json["run"] = course_run

        if display_name is not None:
            course_json["display_name"] = display_name

        self.course_slug = course_slug
        self.course_run = course_run

        try:
            Course.objects.get(slug=course_slug, run=course_run)
            raise Exception(f"Course with slug {course_slug} and run {course_run} already exists")
        except Course.DoesNotExist:
            pass  # That's good. We'll create one now...

        # Get a default import configuration and set with top-level config values.
        course_import_config: CourseMetaConfig = CourseMetaConfig()

        # ...then override with all other config settings if any are set in json...
        import_config_json = course_json.pop("import_config", {})
        if import_config_json:
            for key, value in import_config_json.items():
                try:
                    setattr(course_import_config, key, value)
                except Exception:
                    raise ValidationError(f"Cannot set import_config property {key} to {value}")

        # The serializer will handle creating the Course and CourseCatalogDescription
        # NOT the CourseNode tree and the related UnitBlocks, SubBlocks, etc.

        # We can't just use Serializers all the way down during
        # imports: we need Course to be saved before creating UnitBlocks
        # and SubBlocks and their related items (Assessments), all of which
        # might need a relation an existing course instance.

        # Pop off course_root_node before serializing Course...we'll add it further below.
        course_root_node_json = course_json.pop("course_root_node")

        # Now deserialize the Course and CourseCatalogDescription (without course_root_node)
        course_serializer = IBiologyCoursesCourseSerializer(data=course_json)
        try:
            course_serializer.is_valid(raise_exception=True)
        except Exception as e:
            error_msg = f"Could not import course: {e}"
            logger.exception(error_msg)
            raise ValidationError(detail=error_msg)
        course = course_serializer.save(course_root_node=None)

        # Now that Course is saved, we can use it in the next steps.
        # remove keys on top-level node that shouldn't be present during an import
        for key in ["node_url", "release_datetime", "unit"]:
            try:
                course_root_node_json.pop(key)
            except Exception:
                pass
        course_root_node_json["display_name"] = course.token
        course_root_node_json["slug"] = course.token

        # Pre-process the course node tree to make SCL stuff look like KinesinlMS stuff
        self._pre_process_node(course_root_node_json)

        # NOTE: Kept getting recursion errors when trying to deserialize
        # course_nodes into MPTT, so creating CourseNode tree manually
        course_root_node = self._deserialize_course_node_tree(
            course_node_json=course_root_node_json,
            course=course,
            parent_node=None,
            level=0,
            content_index=0,
            node_index=1,
            course_import_config=course_import_config,
        )
        course.course_root_node = course_root_node
        course.save()

        # Try to set the thumbnail, since we know where the images are stored
        try:
            self._set_course_thumbnail()
        except Exception as e:
            logger.exception(f"Could not set course thumbnail: {e}")

        return course

    def import_course_from_archive(
        self,
        file,
        display_name: str,
        course_slug: str,
        course_run: str,
        options: CourseImportOptions = None,
    ) -> Optional[Course]:
        """
        Load a course and related resources from a course archive (.zip) file.

        Args:
            file:
            display_name:
            course_slug:
            course_run:
            options:            CourseImportOptions instance with options for import.

        Returns:
            Course instance or None
        """

        if file is None:
            raise ValueError("file cannot be None")

        self.update_cache(
            ImportStatus(
                percent_complete=10,
                progress_message=_("Loading course archive"),
            )
        )

        zp = zipfile.ZipFile(file)
        info_list: List[zipfile.ZipInfo] = zp.infolist()
        course_file_zipinfo = None

        self.update_cache(
            ImportStatus(
                percent_complete=20,
                progress_message=_("Reading course archive"),
            )
        )

        for zipinfo in info_list:
            if zipinfo.filename == "course.json":
                course_file_zipinfo = zipinfo
        if not course_file_zipinfo:
            raise Exception("Archive is missing a course.json file at the top level.")

        self.update_cache(
            ImportStatus(
                percent_complete=50,
                progress_message=_("Deserialzing course archive"),
            )
        )

        # Load the course.json file
        course_export_json_raw = zp.read("course.json")
        course_export_json: Dict = json.loads(course_export_json_raw)

        # Check for metadata. For now, we just report to command line log.
        document_type = course_export_json.get("document_type", None)
        if document_type:
            if document_type != KinesinLMSCourseExportFormatID.IBIO_COURSES_FORMAT.value:
                raise Exception(f"Invalid document type for an iBiology Courses course archive: {document_type}")
            metadata = course_export_json.get("metadata", {})
            exporter_version = metadata.get("exporter_version", None)
            export_date = metadata.get("export_date", None)
            logger.info(
                f"Importing a course exported in format: {document_type}. "
                f"Composer exporter version : {exporter_version}. "
                f"Export Date: {export_date} "
            )
        else:
            raise Exception("No document type found in course.json")

        course: Course = self.import_course_from_json(
            course_json=course_export_json,
            display_name=display_name,
            course_slug=course_slug,
            course_run=course_run,
            options=options,
        )

        if options.create_forum_items:
            self.update_cache(
                ImportStatus(
                    percent_complete=60,
                    progress_message=_("Creating forum items"),
                )
            )
            # Set up required forum topics after course import
            try:
                service = get_forum_service()
                service.configure_forum_for_new_course(course=course)
            except Exception:
                raise Exception("Could not configure forum topics.")

        # Set up CourseResources and Resources after the course.json import is complete.
        # We assume the course.json import created or linked:
        # - all CourseResources,
        # - all Resources via BlockResource,
        # ...so now the only task is to load in actual
        # resources files that were created (linked will already be there).
        logger.info("Loading course and block resources: ")
        self.update_cache(
            ImportStatus(
                percent_complete=70,
                progress_message=_("Loading course and block resources"),
            )
        )
        for file_info in info_list:
            if file_info.is_dir():
                continue

            ignore_names = ["course.json", ".DS_Store", "_MACOSX"]
            try:
                for ignore_name in ignore_names:
                    if ignore_name in file_info.filename:
                        raise Exception(f"Skipping file {file_info.filename}")
            except Exception:
                continue

            try:
                file_path = file_info.filename
                filename_parts = file_path.split("/")
                first_filename_part = filename_parts[0]

                if first_filename_part == "course_resources":
                    try:
                        self._load_course_resources(
                            course=course,
                            filename_parts=filename_parts,
                            zp=zp,
                            file_path=file_path,
                        )
                    except Exception as e:
                        logger.exception(f"Could not load course resource file {file_info}")
                        raise e
                elif first_filename_part == "block_resources":
                    try:
                        self._load_block_resources(
                            filename_parts=filename_parts,
                            zp=zp,
                            file_path=file_path,
                            file_info=file_info,
                        )
                    except Exception as e:
                        logger.exception(f"Could not load block resource file {file_info}")
                        raise e
                elif first_filename_part == "catalog":
                    try:
                        self._load_catalog_resources(
                            course=course,
                            filename_parts=filename_parts,
                            zp=zp,
                            file_path=file_path,
                        )
                    except Exception as e:
                        logger.exception(f"Could not load catalog resource file {file_info}")
                        raise e
                else:
                    raise Exception(f"Unknown file path: {file_path}")

            except Exception as e:
                logger.exception(f"Could not save file {file_info}")
                raise e

        self.update_cache(
            ImportStatus(
                percent_complete=90,
                progress_message=_("Validating course import"),
            )
        )

        # Now make sure all Resources were created and have their files defined.
        for course_unit in course.course_units.all():
            for block in course_unit.contents.all():
                for resource in block.resources.all():
                    if not resource.resource_file:
                        logger.error(f"Resource file not found for resource: {resource}")
        return course

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # PRIVATE METHODS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _load_course_resources(
        self,
        filename_parts: List[str],
        course: Course,
        zp: zipfile.ZipFile,
        file_path: str,
    ):
        # We have a course resource file to load.
        # The CourseResource object should already have been created...
        uuid = filename_parts[1]
        file_name = filename_parts[-1]
        course_resource = CourseResource.objects.get(uuid=uuid, course=course)
        if not course_resource.resource_file:
            resource_file_content = zp.read(file_path)
            content_file = ContentFile(resource_file_content)
            course_resource.resource_file.save(file_name, content_file, save=True)
            logger.info(f" - saved file {file_name} to course resource {course_resource}")

    def _load_block_resources(
        self,
        filename_parts: List[str],
        zp: zipfile.ZipFile,
        file_path: str,
        file_info: zipfile.ZipInfo,
    ):
        # We have a resource file to load.
        resource_type = ResourceType[filename_parts[1].upper()]
        uuid = filename_parts[2]
        file_name = filename_parts[-1]
        resource, resource_created = Resource.objects.get_or_create(uuid=uuid)
        if resource_created:
            # We should never really get here, because the Resource model
            # should have been created during the course.json import.
            logger.info(f" - Created new resource: {resource}")
            resource.type = resource_type.name
            resource.save()
        else:
            logger.info(f" - SKIP adding Resource instance for uuid {resource.uuid}. Resource instance already exists.")
            if resource.type != resource_type.name:
                raise Exception(
                    f"Resource type mismatch. You are trying to import a resource "
                    f"with uuid {resource.uuid} and type {resource_type.name}. A resource with that "
                    f"uuid already exists, but it has a different resource type: {resource.type}"
                )

        # Sometimes the Resource model instance will exist, but the actual file in the
        # MEDIA folder does not. Check for that. If it's missing from the media folder,
        # we'll copy it back in. If it doesn't exist (e.g. because it's new), we'll create it.
        if resource.resource_file and resource.resource_file.path:
            media_file_exists = os.path.exists(resource.resource_file.path)
        else:
            media_file_exists = False

        if not media_file_exists:
            resource_file_content = zp.read(file_path)
            content_file = ContentFile(resource_file_content)
            resource.resource_file.save(file_name, content_file, save=True)
            if resource_created:
                logger.info(f" - saved file {file_name} to resource {resource}")
            else:
                logger.info(f" - replaced missing file {file_info} for resource {resource}")

    def _load_catalog_resources(
        self,
        course: Course,
        filename_parts: List[str],
        zp: zipfile.ZipFile,
        file_path: str,
    ):
        # This will be the syllabus or the thumbnail
        if filename_parts[1] == "thumbnail":
            thumbnail_content = zp.read(file_path)
            content_file = ContentFile(thumbnail_content)
            filename = file_path.split("/")[-1]
            extension = filename.split(".")[-1]
            valid_extensions = ["png", "jpg", "jpeg"]
            if extension not in valid_extensions:
                raise Exception(
                    f"Invalid course thumbnail file extension: {extension}. Valid extensions: {valid_extensions}"
                )
            course.catalog_description.thumbnail.save(filename, content_file)
            logger.info(f" - saved course thumbnail {filename}")
        elif filename_parts[1] == "syllabus":
            syllabus_content = zp.read(file_path)
            content_file = ContentFile(syllabus_content)
            filename = file_path.split("/")[-1]
            extension = filename.split(".")[-1]
            valid_extensions = ["pdf", "txt", "md", "docx", "doc"]
            if extension not in valid_extensions:
                raise Exception(
                    f"Invalid course syllabus file extension: {extension}. Valid extensions: {valid_extensions}"
                )
            course.catalog_description.syllabus.save(filename, content_file)
            logger.info(f" - saved course syllabus {filename}")
        else:
            logger.warning(f"Unknown catalog resources file: {file_path}")

    def _deserialize_course_node_tree(
        self,
        course_node_json: Dict,
        course: Course,
        node_index: int,  # noqa: F841
        level: int,
        parent_node: CourseNode = None,
        content_index: Optional[int] = None,
        course_import_config: Optional[CourseMetaConfig] = None,
    ):
        """
        Recursive function to deserialize the nodes of a course node
        tree, as represented in JSON in a course import file.

        DISPLAY SEQUENCE vs CONTENT INDEX:
        Remember that the 'display_sequence' property of CourseNode is
        vital to ordering nodes and must be defined correctly, while the
        'content_index' is just for displaying to the user and does not
        have to be defined (sometimes it's not defined in e.g. modules at
        the end of the course).

        Args:
            course_node_json:       Full json description of the current course node
                                    including any children
            course:                 An instance of the Course model
            node_index:             The index of the current node amongst its peers
            level:                  The level of the node in the tree
                                        0 - root
                                        1 - module
                                        2 - section
                                        3 - unit
            parent_node:            Parent node (None for root node)
            content_index:          The integer to show the student for this node. (Can be None.)
            course_import_config:   Configuration for course import, if any.

        Returns:
            Instance of node created from json description.

        """

        if level > 3:
            logger.warning(f"Should not be a node at level {level}")
            return

        # Set the content_index...
        if level > 0 and content_index is not None:
            logger.debug("Auto content indexing node.")
            existing_value = course_node_json.get("content_index", None)
            if existing_value:
                logger.warning(f"Overwriting content_index: {existing_value} with {content_index}")
            course_node_json["content_index"] = content_index

        level += 1
        children_json = course_node_json.pop("children", None)

        try:
            # if this is a UNIT, node, we'll need to pop off the CourseUnit definition
            # and create separately
            course_unit_json = course_node_json.pop("unit", {})
            node_serializer = CourseNodeSerializer(data=course_node_json, context={"course": course})
        except Exception:
            error_msg = "Could not serialize course nodes."
            logger.exception(error_msg)
            raise ValidationError(detail=error_msg)

        try:
            node_serializer.is_valid(raise_exception=True)
        except Exception:
            error_msg = f"Could not deserialize node {course_node_json}"
            logger.exception(error_msg)
            raise ValidationError(detail=error_msg)
        node = node_serializer.save(parent=parent_node)

        if children_json and isinstance(children_json, list) and len(children_json) > 0:
            # Decide on auto content indexing for children...
            auto_content_start_index = course_import_config.auto_content_start_index(node_type=node.type)
            if auto_content_start_index:
                content_index = auto_content_start_index
            else:
                content_index = None

            for node_index, child_json in enumerate(children_json):
                if not auto_content_start_index:
                    # If we're not auto-content-indexing, we respect the
                    # content-index as defined in the incoming json.
                    content_index = child_json.get("content_index", None)

                # Deserialize each child node.
                if hasattr(child_json, "id"):
                    raise Exception("Incoming CourseNode json cannot have an 'id' property.")
                if hasattr(child_json, "parent"):
                    raise Exception("Incoming CourseNode json cannot have a 'parent' property.")

                self._deserialize_course_node_tree(
                    course_node_json=child_json,
                    course=course,
                    parent_node=node,
                    level=level,
                    node_index=node_index,
                    content_index=content_index,
                    course_import_config=course_import_config,
                )

                if auto_content_start_index:
                    content_index += 1

        if course_unit_json:
            if node.type != NodeType.UNIT.name:
                raise ValidationError("Only nodes of type UNIT can define a 'unit' object.")
            course_unit_serializer = CourseUnitSerializer(
                data=course_unit_json,
                context={
                    "course": course,
                    "course_import_config": course_import_config,
                },
            )
            try:
                course_unit_serializer.is_valid(raise_exception=True)
            except Exception as e:
                logger.exception(f"Could not serialize unit {course_unit_json} : {e}")
                course_slug = course_unit_json.get("slug", "(no slug found)")
                error_msg = f"Could not serialize unit {course_slug}"
                logger.exception(error_msg)
                raise ValidationError(detail=error_msg)

            try:
                course_unit = course_unit_serializer.save(course=course)
            except Exception as e:
                logger.exception(f"Could not save unit {course_unit_json} : {e}")
                error_msg = f"Could not save unit {course_slug}"
                raise ValidationError(detail=error_msg)
            node.unit = course_unit
            node.save()

        return node

    def _pre_process_node(self, node: Dict):
        """
        Recursive function to process nodes in the course nav tree.
        """
        if node is None:
            return
        children = node.get("children", [])
        for child in children:
            try:
                self._pre_process_node(child)
            except Exception as e:
                logger.exception(f"Could not pre-process child {child} : {e}")
                raise e

        unit = node.get("unit", None)
        if unit:
            # This is a unit node, so make any required changes to
            # the "unit" dictionary, which represents a CourseUnit.
            unit_blocks = unit.get("unit_blocks", [])
            for unit_block in unit_blocks:
                try:
                    self._pre_process_unit_block(unit_block)
                except Exception as e:
                    logger.exception(f"Could not pre-process block {unit_block} : {e}")
                    raise e

    def _pre_process_unit_block(self, unit_block: Dict):
        """
        Preprocess a block in the course nav tree to make sure
        we transform any older conventions to the new KinesinLMS format.
        """
        block = unit_block.get("block", {})
        block_type = block.get("type")
        if block_type == "DISCOURSE_TOPIC":
            block["type"] = BlockType.FORUM_TOPIC.name
        elif block_type == "ASSESSMENT":
            assessment = block.get("assessment", {})
            assessment_type = assessment.get("type", None)
            if assessment_type == "MULTIPLE_CHOICE":
                try:
                    if "definition_json" in assessment:
                        definition_json = assessment.pop("definition_json")
                        if "choices" in definition_json:
                            choices = definition_json.get("choices", [])
                            for choice in choices:
                                # change 'choiceKey' key to 'choice_key'
                                if "choiceKey" in choice:
                                    choice["choice_key"] = choice.pop("choiceKey")
                except Exception as e:
                    logger.exception(f"Could not pre-process assessment {assessment} : {e}")
                    raise e
        elif block_type == "SURVEY":
            # Change survey information to match KinesinLMS format
            # In SCL it's stored as json_content, in KinesinLMS it's stored as a SurveyBlock.
            json_content = block.pop("json_content", {})
            survey_type = json_content.get("survey_type", None)
            survey_id = json_content.get("survey_id", None)
            if survey_id:
                try:
                    survey = Survey.objects.get(survey_id=survey_id)
                except Survey.DoesNotExist as dne:
                    logger.exception(f"Survey not found for survey_id {survey_id}")
                    raise dne
            elif survey_type in [
                SurveyType.PRE_COURSE.name,
                SurveyType.POST_COURSE.name,
            ]:
                try:
                    # In iBioV2, early on I wasn't saving the survey_id if the type
                    # was PRE_COURSE or POST_COURSE (thinking there'd be only one of each).
                    # But now that's a pain because I don't have the survey_id to look up the Survey.
                    # So I'll just look up the survey by type and course and assume there's only one.
                    # If there's not this should rightly raise an exception.
                    survey = Survey.objects.get(
                        type=survey_type,
                        course__run=self.course_run,
                        course__slug=self.course_slug,
                    )
                except Survey.DoesNotExist:
                    raise Exception(
                        f"Survey not found for type {survey_type} in course {self.course_slug}-{self.course_run}"
                    )
            else:
                raise Exception("Survey block missing survey_id")

            survey_block = {"survey": survey.slug}
            block["survey_block"] = survey_block

        html_content = block.get("html_content")
        if html_content is not None:
            block["html_content"] = self._update_template_keywords(html_content)

    def _update_template_keywords(self, html_content: str) -> str:
        """
        Transform any SCL-style template keywords to
        Kinesin-style template tags.
        """
        if not html_content:
            return html_content

        replacements = {
            # Simple keywords
            r"\[\[\s*ANON_USER_ID\s*\]\]": "{% anon_user_id %}",
            r"\[\[\s*USERNAME\s*\]\]": "{% username %}",
            # Replace LINK keywords with appropriate template tag.
            r"##MODULE_LINK\[\s*(\d+)\s*\]##": "{{% module_link {} %}}",
            r"##SECTION_LINK\[\s*(\d+)\s*,\s*(\d+)\s*\]##": "{{% section_link {} {} %}}",
            r"##UNIT_LINK\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]##": "{{% unit_link {} {} {} %}}",
            # Other keywords...
            # Transform UNIT_SLUG_LINK
            r"##UNIT_SLUG_LINK\[\s*([A-Za-z\d\-\_]+)\s*\]##": "{{% unit_slug_link {} %}}",
        }

        for pattern, replacement in replacements.items():
            html_content = re.sub(pattern, lambda match: replacement.format(*match.groups()), html_content)

        return html_content

    def _set_course_thumbnail(self) -> bool:
        """
        Try to set the course thumbnail by looking for it in the
        iBiov2 public s3 bucket.

        Returns:
            True if the thumbnail was set, False otherwise.

        """

        thumbnail_image_filename = f"{self.course_slug.lower()}_thumbnail.png"
        thumbnail_url = f"https://ibio-v2.s3.amazonaws.com/static/catalog/images/{thumbnail_image_filename}"

        # Try to download the thumbnail image
        # and save as the course thumbnail in CourseCatalogDescription.

        try:
            response = requests.get(thumbnail_url)
            response.raise_for_status()
            ccd = CourseCatalogDescription.objects.get(
                course__slug=self.course_slug,
                course__run=self.course_run,  # Fixed typo in 'course'
            )
            content_file = ContentFile(response.content)  # Using .content instead of .read()
            ccd.thumbnail.save(thumbnail_image_filename, content_file, save=True)
            logger.info(f"Saved course thumbnail: {thumbnail_image_filename}")
        except Exception as e:
            logger.exception(f"Could not set course thumbnail: {e}")
            return False

        return True
