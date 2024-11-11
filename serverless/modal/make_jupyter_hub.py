import logging
import os
import shutil
import subprocess
from pathlib import Path
from secrets import token_urlsafe
from typing import Dict, List

import modal

from config import config_jupyterlab

# Configuration
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

JUPYTER_PORT = 8888
# By convention, we're storing JupyterLab .ipynb files as the
# 'file_resource' File property of a KinesinLMS 'Resource' model.
# These files will be stored in the '/media/block_resources' directory
# of the 'kinesinlms' bucket on S3. So we'll read them straight from
# there as we've stored the S3 credentials in the 'aws-s3-bucket-secrets' variable.
AWS_MOUNT_PATH = Path("/kinesinlms")
AWS_BLOCK_RESOURCES_PATH = AWS_MOUNT_PATH / "media" / "block_resources"
RESOURCES_PATH = Path("/resources_data")

# Define a secret to store the AWS S3 credentials
# The app is going to read in the notebook as well as any
# accompanying resources from the S3 bucket.
s3_secret = modal.Secret.from_name(
    "aws-s3-bucket-secrets",
    required_keys=[
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ],
)

# Apps and Volumes
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Define a persistent volume for KinesinLMS resources
# e.g. SQLite databases, CSV files, etc.
resources_volume = modal.Volume.from_name(
    "resources-data-volume",
    create_if_missing=True,
)

# This is the modal app that's going to run the Jupyter Lab server.
app = modal.App("my_jupyter_hub")
app.image = modal.Image.debian_slim().pip_install(
    "jupyterlab",
    "matplotlib",
    "pandas",
    "numpy",
    "sqlalchemy",
    "scipy",
)


# JUPYTER LAB SERVER
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@app.function(
    timeout=1_500,
    volumes={
        AWS_MOUNT_PATH: modal.CloudBucketMount(
            bucket_name="kinesinlms",
            read_only=True,
            secret=s3_secret,
        ),
        RESOURCES_PATH: resources_volume,
    },
)
def run_jupyter(
    q,
    notebook_filename=None,
    resources: List[Dict] = [],
    extra_pip_packages=[],
    access_token=None,
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

    if not access_token:
        access_token = token_urlsafe(16)

    if extra_pip_packages:
        print(f"run_jupyter(): Installing packages: {extra_pip_packages}")
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

    # Create config and workspace directories if they don't exist
    os.makedirs("/root/.jupyter", exist_ok=True)
    workspace_dir = Path("/root/workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    local_notebook_path = None
    if notebook_filename:
        # HANDLE INCOMING NOTEBOOK
        # Copy notebook file if provided so that it's available in the workspace
        # immediately upon starting Jupyter Lab.
        try:
            s3_path = AWS_BLOCK_RESOURCES_PATH / notebook_filename
            local_notebook_path = workspace_dir / notebook_filename
            print(
                f"run_jupyter(): Copying notebook from {s3_path} to {local_notebook_path}"
            )
            shutil.copy2(s3_path, local_notebook_path)
            print(
                f"run_jupyter()  - successfully copied notebook from {s3_path} to "
                f"{local_notebook_path}"
            )

        except Exception as e:
            logger.error(f"Error copying notebook file: {e}")
            raise

    if resources:
        # HANDLE INCOMING KINESINLMS RESOURCES
        # Store them in the attached volume so they're available to the notebook
        print("run_jupyter(): Processing resources...")
        os.makedirs(RESOURCES_PATH, exist_ok=True)
        for resource in resources:
            print(
                f"run_jupyter():  - resource type: {resource.get('type')} "
                f"filename: {resource.get('filename')}"
            )
            try:
                filename = resource.get("filename")
                resource_type = resource.get("type")

                if not filename or not resource_type:
                    logger.warning(
                        f"run_jupyter(): Skipping resource with missing "
                        f"filename or type: {resource}"
                    )
                    continue

                s3_path = AWS_BLOCK_RESOURCES_PATH / filename

                # For SQLite files, copy to workspace to match notebook's working dir
                if resource_type in ["SQLITE", "CSV"]:
                    # Extract just the filename without path
                    base_filename = Path(filename).name
                    dest_path = workspace_dir / base_filename
                    print(
                        f"  - copying {resource_type} file "
                        f"from {s3_path} "
                        f"to {dest_path}"
                    )
                    shutil.copy2(s3_path, dest_path)
                    os.chmod(dest_path, 0o666)  # Ensure file permissions allow rw
                    print(
                        f"run_jupyter():   - successfully copied "
                        f"SQLite file: {base_filename}"
                    )
                else:
                    print(f"run_jupyter(): Unsupported resource type: {resource_type}")

            except Exception as e:
                logger.error(f"run_jupyter(): Error copying resource {filename}: {e}")
                raise
    else:
        print("run_jupyter(): No resources!")

    for resource in resources:
        resource_type = resource.get("type")
        if resource_type == "SQLITE":
            # Even thought we already saved the sqlite file to the workspace,
            # we still need to store the actual database file that sqlite
            # creates when it opens the database. We'll store it in the
            # resources directory so that it's available to the notebook.
            os.environ["SQLITE_DATABASE_PATH"] = str(RESOURCES_PATH / "database.db")

    config_jupyterlab(notebook_filename=notebook_filename)

    print("Starting Jupyter Lab as tunnel...")
    with modal.forward(JUPYTER_PORT) as tunnel:
        url = tunnel.url + "/?token=" + access_token

        q.put(url, block=False)
        print(f"run_jupyter(): Starting Jupyter at {url}")

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
            env={**os.environ, "JUPYTER_TOKEN": access_token, "SHELL": "/bin/bash"},
        )


# SPAWN JUPYTER LAB (FAKE JUPYTER HUB)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@app.function()
def spawn_jupyter(
    notebook_filename=None,
    extra_pip_packages=[],
    resources=[],
    access_token=None,
):
    """
    Spawn a Jupyter Lab server and return the URL.

    Args:
        notebook_filename:str           The filename of an .ipynb file stored
                                        in the 'block_resources' directory on S3.
        extra_pip_packages: list        A list of extra pip packages to install.
        resources: list                 A list of KinesinLMS 'resources' that
                                        accompany the notebook (e.g. a SQLite file).
        access_token: str               A secret token to authenticate the user.

    Raises:
        Exception

    Returns:
        The URL of the Jupyter Lab server.
    """
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

            print("spawn_jupyter(): spawinging Jupyter Lab...")
            run_jupyter.spawn(
                q,
                notebook_filename=notebook_filename,
                extra_pip_packages=extra_pip_packages,
                resources=resources,
                access_token=access_token,
            )
            print("spawn_jupyter(): Getting Jupyter Lab url...")
            url = q.get()
            print(f"spawn_jupyter(): Jupyter is ready at {url}")
            return url
    else:
        raise Exception("Not authenticated")
