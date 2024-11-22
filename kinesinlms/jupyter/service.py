import logging
from typing import Dict, List

import modal

logger = logging.getLogger(__name__)


class TooManyNotebooksError(Exception):
    pass


class JupyterService:
    """
    Provides service methods for operations on the Modal.com
    external tool.
    """

    def __init__(self, *args, throttle=10, **kwargs):
        """
        Initializes the Modal.com external tool service with the given API key.

        Args:
            throttle (int): The maximum number of notebooks that can be run at once
        """
        super().__init__(*args, **kwargs)
        self.throttle = throttle

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

        logger.info("Launching jupyter notebook in Modal.com...")

        extra_pip_packages = []  # ["pynbody"]

        spawn_jupyter_remote_function = modal.Function.lookup(
            "my_jupyter_hub",
            "spawn_jupyter",
        )

        function_stats: modal.functions.FunctionStats = (
            spawn_jupyter_remote_function.get_current_stats()
        )

        if function_stats.num_total_runners >= self.throttle:
            raise TooManyNotebooksError(
                "Too many notebooks are currently running. Please try again later."
            )

        launch_url = spawn_jupyter_remote_function.remote(
            notebook_filename=notebook_filename,
            extra_pip_packages=extra_pip_packages,
            resources=resources,
        )
        logger.info(f"Jupyter notebook launched successfully. URL: {launch_url}")
        return launch_url
