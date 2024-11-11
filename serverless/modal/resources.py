import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_resource(
    filename: str,
    resource_type: str,
    aws_resource_path: Path,
) -> bool:
    """Validate a resource before processing it."""
    # Prevent path traversal
    if ".." in filename or filename.startswith("/"):
        raise Exception(f"Invalid filename path: {filename}")

    # Validate resource type
    valid_types = ["SQLITE", "CSV"]
    if resource_type not in valid_types:
        raise Exception(f"Invalid resource type: {resource_type}")

    # Validate file exists in S3 path
    s3_path = aws_resource_path / filename
    if not s3_path.exists():
        raise Exception(f"File does not exist: {s3_path}")

    # Check file size (e.g., limit to 1GB)
    if s3_path.stat().st_size > 1_000_000_000:  # 1GB
        raise Exception(f"File too large: {filename}")

    return True
