import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import modal

# Define a persistent volume for SQLite
sqlite_volume = modal.Volume.from_name("sqlite-data-volume", create_if_missing=True)

app = modal.App("my_jupyter_hub")
app.image = modal.Image.debian_slim().pip_install(
    "jupyterlab", "matplotlib", "pandas", "numpy", "sqlalchemy", "scipy"
)

s3_secret = modal.Secret.from_name(
    "aws-s3-bucket-secrets",
    required_keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
)


# By convention, we're storing JupyterLab ipynb files as the
# 'file_resource' File property of a Django 'Resource' model.
# These files will be stored in the '/media/block_resources' directory
# of the 'kinesinlms' bucket on S3. So we'll read them straight from
# there as we've stored the  S3 credentials in the 'saws-s3-bucket-secrets' variable.
MOUNT_PATH = Path("/kinesinlms")
BLOCK_RESOURCES_PATH = MOUNT_PATH / "media" / "block_resources"
SQLITE_PATH = Path("/sqlite_data")

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
        SQLITE_PATH: sqlite_volume,
    },
)
def run_jupyter(
    q,
    notebook_filename=None,
    resources: List[Dict] = [],
    extra_pip_packages=[],
):
    """
    Start a Jupyter Lab server and return the URL.

    Args:
        q (modal.Queue):    A queue to pass the URL back to the caller.
        resources:          A list of resources that accompany the notebook.
                            Resources are stored in the same 'block_resources'
                            directory as the notebook file.
                            The dictionary has two keys:
                            - 'filename': the name of the file, may include subdirs
                            - 'type': type of the resource (e.g. 'CSV', 'SQLITE', ...)

        notebook_filename (str):    The name of the notebook file to open
                                    in Jupyter Lab. This file should be present in the
                                    `MOUNT_PATH` directory.

    Returns:
        ( nothing. The URL is passed back to the caller via the `q` queue. )
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if extra_pip_packages:
        print(f"Installing packages: {extra_pip_packages}")
        try:
            subprocess.check_call(
                [
                    "pip",
                    "install",
                    "--user",
                    "--quiet",
                    "--no-cache-dir",
                    *extra_pip_packages,
                ]
            )
            logging.info("Package installation completed successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install packages: {e}")
            raise
        print("  - done installing packages.")

    print(f"Starting Jupyter Lab. notebook_filename: {notebook_filename}")

    jupyter_port = 8888
    token = "1234"  # temp

    # Create config and workspace directories if they don't exist
    os.makedirs("/root/.jupyter", exist_ok=True)
    workspace_dir = Path("/root/workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    # HANDLE INCOMING NOTEBOOK
    # Copy notebook file if provided so that it's available in the workspace
    # immediately upon starting Jupyter Lab.
    local_notebook_path = None
    if notebook_filename:
        try:
            s3_path = BLOCK_RESOURCES_PATH / notebook_filename
            local_notebook_path = workspace_dir / notebook_filename
            print(f"Copying notebook from {s3_path} to {local_notebook_path}")
            shutil.copy2(s3_path, local_notebook_path)
            print(
                f"  - successfully copied notebook from {s3_path} to "
                f"{local_notebook_path}"
            )

        except Exception as e:
            logger.error(f"Error copying notebook file: {e}")
            raise

    # HANDLE INCOMING RESOURCES
    if resources:
        print("Processing resources...")
        for resource in resources:
            print(
                f" - resource type: {resource.get('type')} "
                f"filename: {resource.get('filename')}"
            )
            try:
                filename = resource.get("filename")
                resource_type = resource.get("type")

                if not filename or not resource_type:
                    logger.warning(
                        f"Skipping resource with missing filename or type: {resource}"
                    )
                    continue

                s3_path = BLOCK_RESOURCES_PATH / filename

                # For SQLite files, copy to workspace to match notebook's working dir
                if resource_type in ["SQLITE", "CSV"]:
                    # Extract just the filename without path
                    base_filename = Path(filename).name
                    dest_path = workspace_dir / base_filename
                    print(
                        f"  - copying {resource_type} file from {s3_path} "
                        f"to {dest_path}"
                    )
                    shutil.copy2(s3_path, dest_path)
                    os.chmod(dest_path, 0o666)  # Ensure file permissions allow rw
                    print(f"  - successfully copied SQLite file: {base_filename}")
                else:
                    print(f"Unsupported resource type: {resource_type}")

            except Exception as e:
                logger.error(f"Error copying resource {filename}: {e}")
                raise
    else:
        print("### No resources!")

    # Create jupyter_server_config.py with the CSP headers
    # we need to be able to load the Jupyter Lab in an iFrame.
    print("Saving Jupyter config...")
    config = """
c.ServerApp.tornado_settings = {
    "headers": {
        "Content-Security-Policy": "default-src 'self' * 'unsafe-inline' 'unsafe-eval' ws: wss: blob: data:; "
        "frame-ancestors 'self' *;",
        "X-Frame-Options": "ALLOW-FROM https://kinesinlms-8b588e478a49.herokuapp.com http://localhost:8001"
    }
}
c.ServerApp.root_dir = '/root/workspace'
    """

    # style-src 'self' https://kinesinlms-8b588e478a49.herokuapp.com; script-src 'self' https://kinesinlms-8b588e478a49.herokuapp.com; connect-src 'self' wss://*;

    # Add notebook-specific configuration if a notebook is provided
    if notebook_filename:
        config += f"""
c.LabApp.default_url = '/lab/tree/{notebook_filename}'
"""

    # Write config to file
    with open("/root/.jupyter/jupyter_server_config.py", "w") as f:
        f.write(config)
    print("  - done saving Jupyter config")

    # Create SQLite directory if it doesn't exist
    os.makedirs(SQLITE_PATH, exist_ok=True)

    # Set environment variable for SQLite database path
    os.environ["SQLITE_DATABASE_PATH"] = str(SQLITE_PATH / "database.db")

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
        )


# SPAWN JUPYTER LAB (FAKE JUPYTER HUB)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.function()
def spawn_jupyter(
    notebook_filename=None,
    extra_pip_packages=[],
    resources=[],
):
    # do some validation on the secret or bearer token
    is_valid = True

    if is_valid:
        with modal.Queue.ephemeral() as q:
            print(
                f"spawn_jupyter(): Spawning Jupyter with "
                f"notebook {notebook_filename} "
                f"resources : {resources}."
            )
            if extra_pip_packages:
                print(f"  -  Extra pip packages: {extra_pip_packages}")
            run_jupyter.spawn(
                q,
                notebook_filename=notebook_filename,
                extra_pip_packages=extra_pip_packages,
                resources=resources,
            )
            print("spawn_jupyter(): Getting url...")
            url = q.get()
            print(f"spawn_jupyter(): Jupyter is ready at {url}")
            return url
    else:
        raise Exception("Not authenticated")
