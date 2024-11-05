import logging
from typing import Type

from django.core.exceptions import ValidationError

from kinesinlms.external_tools.constants import ExternalToolProviderType
from kinesinlms.external_tools.service.base_service import BaseExternalToolService
from kinesinlms.external_tools.service.modal_service import ModalComExternalToolService

logger = logging.getLogger(__name__)

class ExternalToolServiceFactory:
    _services: dict[str, Type[BaseExternalToolService]] = {
        ExternalToolProviderType.JUPYTER_LAB.name: ModalComExternalToolService,
    }

    @classmethod
    def create_service(cls, tool_type: str) -> BaseExternalToolService:
        """
        Creates and returns the appropriate service instance based on
        the external tool type.

        Args:
            tool_type: String representation of the tool type (e.g., "RENDER", "AMAZON")

        Returns:
            An instance of the appropriate service class

        Raises:
            ValidationError: If the tool type is not supported
        """
        assert tool_type, "Tool type must be provided"
        assert tool_type in [
            item.name for item in ExternalToolProviderType
        ], "Invalid tool type"

        try:
            service_class = cls._services.get(tool_type)
            if not service_class:
                raise ValidationError(f"Unsupported tool type: {tool_type}")
            return service_class()
        except ValueError:
            raise ValidationError(f"Invalid tool type: {tool_type}")
        except Exception as e:
            logger.exception(f"Error creating service for tool type: {tool_type} e: {e}")
            raise ValidationError(f"Error creating service for tool type: {tool_type}")
