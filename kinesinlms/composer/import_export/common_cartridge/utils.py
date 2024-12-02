import logging
import re

logger = logging.getLogger(__name__)


def validate_resource_path(path: str) -> bool:
    """
    Validate that resource paths follow Common Cartridge specifications.

    Common Cartridge path requirements:
    1. Must use forward slashes (/) not backslashes
    2. Cannot start with a slash
    3. Cannot contain consecutive slashes
    4. Cannot contain spaces or special characters except - and _
    5. Should be case-sensitive
    6. Cannot use reserved names like CON, PRN, AUX, etc (Windows reserved)
    7. Cannot contain parent directory references (..)
    8. Should be relative paths only

    Args:
        path: The resource path to validate

    Returns:
        bool: True if path is valid according to CC specs
    """
    if not path:
        return False

    # Windows reserved filenames
    RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "LPT1", "LPT2", "LPT3", "LPT4"}

    try:
        # Check for absolute paths
        if path.startswith("/"):
            logger.error(f"Resource path cannot start with slash: {path}")
            return False

        # Check for parent directory traversal
        if ".." in path:
            logger.error(f"Resource path cannot contain parent directory references: {path}")
            return False

        # Check for consecutive slashes
        if "//" in path:
            logger.error(f"Resource path cannot contain consecutive slashes: {path}")
            return False

        # Split path into components
        parts = path.split("/")

        # Check each path component
        for part in parts:
            # Check for Windows reserved names
            if part.upper() in RESERVED_NAMES:
                logger.error(f"Resource path contains reserved name: {part}")
                return False

            # Check for valid characters (letters, numbers, hyphen, underscore)
            if not re.match(r"^[\w\-\.]+$", part):
                logger.error(f"Resource path contains invalid characters: {part}")
                return False

            # Check for spaces
            if " " in part:
                logger.error(f"Resource path cannot contain spaces: {part}")
                return False

        return True

    except Exception as e:
        logger.error(f"Error validating resource path {path}: {str(e)}")
        return False
