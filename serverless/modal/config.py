# Use this if we're trying to run Jupyter Lab in an iFrame
# Note that it doesn't really work because websockets are blocked by the browser
# I think there are still some things to be resolved for that to work.
JUPYTER_SERVER_CONFIG_IN_IFRAME = """
c.ServerApp.tornado_settings = {
    "headers": {
        "Content-Security-Policy": "default-src 'self' * 'unsafe-inline' 'unsafe-eval' ws: wss: blob: data:; "
        "frame-ancestors 'self' *;",
        "X-Frame-Options": "ALLOW-FROM https://kinesinlms-8b588e478a49.herokuapp.com http://localhost:8001"
    }
}
c.ServerApp.root_dir = '/root/workspace'
c.LabApp.check_for_updates_class="jupyterlab.NeverCheckForUpdate"
"""

JUPYTER_SERVER_CONFIG = """
c.ServerApp.root_dir = '/root/workspace'
c.LabApp.check_for_updates_class='jupyterlab.NeverCheckForUpdate'
"""


def config_jupyterlab(notebook_filename: str = None):
    # Create jupyter_server_config.py with the CSP headers
    # we need to be able to load the Jupyter Lab in an iFrame.
    config = JUPYTER_SERVER_CONFIG

    if notebook_filename:
        config += f"c.LabApp.default_url = '/lab/tree/{notebook_filename}'"

    print("full JupyterLab config is:")
    print(config)

    # Write config to file
    with open("/root/.jupyter/jupyter_server_config.py", "w") as f:
        f.write(config)
    print("  - done saving Jupyter config")
