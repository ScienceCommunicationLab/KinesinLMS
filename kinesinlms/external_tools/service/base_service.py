class BaseExternalToolService:
    """
    Base class for external tool services.
    Child classes provide service methods for particular external tools.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the external tool service.
        """
        pass

    def get_launch_url(self, external_tool_view: "external_tools.ExternalToolView"):
        """
        Returns the URL to launch the external tool.
        """
        pass