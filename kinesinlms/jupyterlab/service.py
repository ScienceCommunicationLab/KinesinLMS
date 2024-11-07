import logging
from typing import Dict, List

import modal

logger = logging.getLogger(__name__)


class JupyterLabService:
    """
    Provides service methods for operations on the Modal.com
    external tool.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the Modal.com external tool service with the given API key.
        """
        super().__init__(*args, **kwargs)

    def get_launch_url(
        self,
        *args,
        notebook_filename: str = None,
        resources: List[Dict] = [],
        **kwargs,
    ):
        """
        Launches the Modal.com external tool in a new window.
        """

        # temp
        extra_pip_packages = []  # ["pynbody"]

        logger.info("Launching jupyter notebook in Modal.com...")
        spawn_jupyter_remote_function = modal.Function.lookup(
            "my_jupyter_hub",
            "spawn_jupyter",
        )
        launch_url = spawn_jupyter_remote_function.remote(
            notebook_filename=notebook_filename,
            extra_pip_packages=extra_pip_packages,
            resources=resources,
        )
        logger.info(f"Jupyter notebook launched successfully. URL: {launch_url}")
        return launch_url
