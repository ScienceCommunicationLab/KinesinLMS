import base64
import logging
import os
import shutil
import subprocess
from pathlib import Path

import modal

app = modal.App("my_jupyter_hub")
app.image = modal.Image.debian_slim().pip_install(
    "jupyterlab",
    "matplotlib==3.8.3",
)

s3_secret = modal.Secret.from_name(
    "aws-s3-bucket-secrets",
    required_keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
)

MOUNT_PATH: Path = Path("/modal_test")
NOTEBOOKS_PATH: Path = MOUNT_PATH / "notebooks"

# Persistent volume for storing notebooks
volume = modal.Volume.from_name(
    "jupyter-notebooks-volume",
    create_if_missing=True,
)


MOUNT_PATH: Path = Path("/kinesinlms")

# JUPYTER LAB SERVER
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Function that starts a Jupyter server
# and returns a URL for a student to access it.
@app.function(
    timeout=1_500,
    volumes={
        MOUNT_PATH: modal.CloudBucketMount(
            bucket_name="kinesinlms",
            read_only=True,
            secret=s3_secret,
        ),
    },
)
def run_jupyter(q, notebook_filename=None):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    print(f"Starting Jupyter Lab. notebook_filename: {notebook_filename}")

    jupyter_port = 8888
    token = "1234"  # temp

    # Create config and workspace directories if they don't exist
    os.makedirs("/root/.jupyter", exist_ok=True)
    workspace_dir = Path("/root/workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    # Copy notebook file if provided
    local_notebook_path = None
    if notebook_filename:
        try:
            # Convert paths to Path objects
            s3_path = MOUNT_PATH / "tmp_notebooks" / notebook_filename
            local_notebook_path = workspace_dir / notebook_filename

            print(f"Copying notebook from {s3_path} to {local_notebook_path}")

            # Copy the file directly
            shutil.copy2(s3_path, local_notebook_path)
            print(
                f"Successfully copied notebook from {s3_path} to "
                f"{local_notebook_path}"
            )

        except Exception as e:
            logger.error(f"Error copying notebook file: {e}")
            raise

    # Create jupyter_server_config.py with CSP headers
    print("Saving Jupyter config...")
    config = """
c.ServerApp.tornado_settings = {
    'headers': {
        'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data:; "
        "frame-ancestors 'self' *; "
        "frame-src 'self' blob: data:; "
        "connect-src 'self' wss://* https://*; "
        "worker-src 'self' blob:; "
        "img-src 'self' blob: data:; "
        "media-src 'self' blob: data:;",
        'X-Content-Type-Options': 'nosniff'
    }
}
c.ServerApp.root_dir = '/root/workspace'
    """
    
    # Add notebook-specific configuration if a notebook is provided
    if notebook_filename:
        config += f"""
c.LabApp.default_url = '/lab/tree/{notebook_filename}'
"""

    # Write config to file
    with open("/root/.jupyter/jupyter_server_config.py", "w") as f:
        f.write(config)
    print("  - done saving Jupyter config")

    print("Starting Jupyter Lab as tunnel...")
    with modal.forward(jupyter_port) as tunnel:
        url = tunnel.url + "/?token=" + token

        q.put(url, block=False)
        print(f"Starting Jupyter at {url}")

        subprocess.run(
            [
                "jupyter",
                "lab",
                "--no-browser",
                "--allow-root",
                "--ip=0.0.0.0",
                "--port=8888",
                "--LabApp.allow_origin='*'",
                "--LabApp.allow_remote_access=1",
            ],
            env={**os.environ, "JUPYTER_TOKEN": token, "SHELL": "/bin/bash"},
            stderr=subprocess.DEVNULL,
        )


# SPAWN JUPYTER LAB (FAKE JUPYTER HUB)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.function()
def spawn_jupyter(notebook_filename=None):
    # do some validation on the secret or bearer token
    is_valid = True

    if is_valid:
        with modal.Queue.ephemeral() as q:
            print("spawn_jupyter(): Spawning Jupyter")
            run_jupyter.spawn(q, notebook_filename)
            print("spawn_jupyter(): Getting url...")
            url = q.get()
            print(f"spawn_jupyter(): Jupyter is ready at {url}")
            return url
    else:
        raise Exception("Not authenticated")
