from enum import Enum


class CourseExportFormat(Enum):
    KINESIN_LMS_ZIP = "Kinesin LMS JSON Format"
    COMMON_CARTRIDGE_FULL = "Common Cartridge Format (Full)"
    COMMON_CARTRIDGE_SLIM = "Common Cartridge Format (Slim)"
    OPEN_EDX = "Open edX Format"
