from enum import Enum


class CourseExportFormatID(Enum):
    KINESIN_LMS_FORMAT = "kinesinlms:course_export"
    SCL_FORMAT = "ibiology_courses:course_export"


VALID_COURSE_EXPORT_FORMAT_IDS = [
    CourseExportFormatID.KINESIN_LMS_FORMAT.value,
    CourseExportFormatID.SCL_FORMAT.value,
]


class CourseExportFormat(Enum):
    KINESIN_LMS_ZIP = "Kinesin LMS JSON Format"


class CommonCartridgeExportFormat(Enum):
    CC_FULL = "Full Common Cartridge Format"
    CC_SLIM = "Slim Common Cartridge Format"
    # Others?


class ImportCopyType(Enum):
    """
    Different ways an object can
    be copied from existing database
    when doing an import.
    """

    SHALLOW = "shallow"


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
