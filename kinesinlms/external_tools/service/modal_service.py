import logging
from time import sleep

import modal

from kinesinlms.external_tools.service.base_service import BaseExternalToolService

logger = logging.getLogger(__name__)


class ModalComExternalToolService(BaseExternalToolService):
    """
    Provides service methods for operations on the Modal.com
    external tool.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the Modal.com external tool service with the given API key.
        """
        super().__init__(*args, **kwargs)

    def get_launch_url(self, external_tool_view: "external_tools.ExternalToolView"):
        """
        Launches the Modal.com external tool in a new window.
        """

        # Launch a Jupyter notebook in modal.com and return the URL

        logger.info("Launching Modal.com external tool...")

        f = modal.Function.lookup("my_jupyter_hub", "spawn_jupyter")
        launch_url = f.remote()
        logger.info(f"Jupyter notebook launched successfully. URL: {launch_url}")
        return launch_url
