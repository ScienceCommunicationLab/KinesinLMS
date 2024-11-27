from enum import Enum


class CommonCartridgeExportDir(Enum):
    # Constants used to reference BlockResource files in the Common Cartridge export
    WEB_RESOURCES_DIR = "web_resources/"
    IMS_CC_ROOT_DIR = "$IMS-CC-FILEBASE$/"


class CommonCartridgeExportFormat(Enum):
    CC_FULL = "Full Common Cartridge Format"
    CC_SLIM = "Slim Common Cartridge Format"
    # Others?


class CommonCartridgeResourceType(Enum):
    # Basic Content Types
    WEB_CONTENT = "webcontent"
    WEB_LINK = "imswl_xmlv1p3"

    # Assessment Types
    QTI_1_2 = "imsqti_xmlv1p2"
    QTI_2_1 = "imsqti_xmlv2p1"
    QTI_ASSESSMENT = "imsqti_assessmentv1p2"
    QTI_QUESTION_BANK = "imsqti_questionbankv1p2"

    # Learning Tools & Resources
    LTI = "imsbasiclti_xmlv1p0"
    BASIC_LTI_LINK = "blti-1.0-link"
    LEARNING_RESOURCE = "associatedcontent/imscc_xmlv1p1/learning-application-resource"

    # Discussion & Interaction
    DISCUSSION_TOPIC = "imsdt_xmlv1p3"
    FORUM = "forum-v1.0"

    # Assignment Types
    ASSIGNMENT = "assignment_xmlv1p0"

    # Package Types
    COURSE_PACKAGE = "imscc_xmlv1p3"

    # File Types
    FILE = "file"
    FOLDER = "folder"

    # Metadata
    COURSE_SETTINGS = "course_settings"
    LEARNING_OUTCOMES = "learning_outcomes"

    # Helper method for QTI types
    @classmethod
    def is_qti(cls, resource_type: str) -> bool:
        return resource_type in [
            cls.QTI_1_2.value,
            cls.QTI_2_1.value,
            cls.QTI_ASSESSMENT.value,
            cls.QTI_QUESTION_BANK.value,
        ]


NAMESPACES = {
    # None is the default namespace
    None: "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
    "lom": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/resource",
    "lomimscc": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "csmd": "http://www.imsglobal.org/xsd/imsccv1p3/csmd_v1p0",
}

# Define schema locations - one per line for readability
SCHEMA_LOCATIONS = [
    "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
    "http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_imscp_v1p2_v1p0.xsd",
    "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/resource",
    "http://www.imsglobal.org/profile/cc/ccv1p3/LOM/ccv1p3_lomresource_v1p0.xsd",
    "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest",
    "http://www.imsglobal.org/profile/cc/ccv1p3/LOM/ccv1p3_lommanifest_v1p0.xsd",
    "http://www.imsglobal.org/xsd/imsccv1p3/csmd_v1p0",
    "http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_csmd_v1p0.xsd",
]
