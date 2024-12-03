from enum import Enum


class CommonCartridgeExportDir(Enum):
    # Constants used to reference BlockResource files in the Common Cartridge export
    WEB_RESOURCES_DIR = "web_resources"
    IMS_CC_ROOT_DIR = "$IMS-CC-FILEBASE$"


class CommonCartridgeExportFormat(Enum):
    CC_FULL = "Full Common Cartridge Format"
    CC_SLIM = "Slim Common Cartridge Format"
    # Others?


class CommonCartridgeResourceType(Enum):
    # Basic Content Types
    WEB_CONTENT = "webcontent"
    WEB_LINK = "imswl_xmlv1p3"

    # Assessment Types - needs update
    QTI_ASSESSMENT = "imsqti_xmlv1p2/imscc_xmlv1p3/assessment"
    QTI_QUESTION_BANK = "imsqti_xmlv1p2/imscc_xmlv1p3/question-bank"

    # Learning Tools & Resources
    BASIC_LTI_LINK = "imsbasiclti_xmlv1p3"
    LEARNING_RESOURCE = "associatedcontent/imscc_xmlv1p3/learning-application-resource"

    # Discussion & Interaction
    DISCUSSION_TOPIC = "imsdt_xmlv1p3"

    # Assignment Types
    ASSIGNMENT = "assignment_xmlv1p3"

    @classmethod
    def is_qti(cls, resource_type: str) -> bool:
        return "imsqti_xmlv1p2/imscc_xmlv1p3" in resource_type


NAMESPACES = {
    # None is the default namespace
    None: "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
    "lom": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/resource",
    "lomimscc": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "csmd": "http://www.imsglobal.org/xsd/imsccv1p3/csmd_v1p0",
    "qti": "http://www.imsglobal.org/xsd/imsqti_v2p1",
    "qtimetadata": "http://www.imsglobal.org/xsd/imsmd_v1p2",
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
