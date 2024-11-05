from enum import Enum


class ExternalToolViewLaunchType(Enum):
    """
    What UI user is shown to start engaging
    with the external tool.
    """

    WINDOW = "window"
    IFRAME = "iframe"


class ExternalToolProviderType(Enum):
    # TODO:
    #   Just learning about juypter notebook hosting
    #   so I could be way off here. But starting
    #   with services based on JupyterLab.
    BASIC_LTI13 = "Basic LTIv1.3"
    
    # KinesinLMS implementation using Modal.com
    JUPYTER_LAB = "JupyterLab"

    # ZTJH implementation using LTIAutheticator
    JUPYTER_HUB = "Modal.com"

    RENKU = "Renku"


class ConnectionMethodType(Enum):
    # TODO:
    #   Just assume manual entry for now
    MANUAL = "manual"


class LTIVersionType(Enum):
    LTI_1_3 = "LTI 1.3"
    # LTI_1_1 = "LTI 1.1"
    # LTI_1_0 = "LTI 1.0"
    # LTI_2_0 = "LTI 2.0"


class LTI1P3SystemCoreRoles(Enum):
    ADMINISTRATOR = "http://purl.imsglobal.org/vocab/lis/v2/system/person#Administrator"


class LTI1P3InstitutionCoreRoles(Enum):
    """
    LTI 1.3 roles
    """

    ADMINISTRATOR = (
        "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Administrator"
    )
    FACULTY = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Faculty"
    GUEST = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Guest"
    NONE = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#None"
    OTHER = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Other"
    STAFF = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Staff"
    STUDENT = "http://purl.imsglobal.org/vocab/lis/v2/institution/person#Student"
