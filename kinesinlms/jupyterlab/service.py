import logging

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

    def get_launch_url(self, *args, **kwargs):
        """
        Launches the Modal.com external tool in a new window.
        """

        logger.info("Launching jupyter notebook in Modal.com...")
        spawn_jupyter_remote_function = modal.Function.lookup(
            "my_jupyter_hub",
            "spawn_jupyter",
        )
        launch_url = spawn_jupyter_remote_function.remote(
            notebook_filename="hello_world.ipynb"
        )
        logger.info(f"Jupyter notebook launched successfully. URL: {launch_url}")
        return launch_url
