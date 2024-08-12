# Local Discourse Setup

In order to use forums when developing locally, you'll need to set up a local instance of Discourse. This is because the
Discourse website does not have a way to create 'test' accounts, so you'll need to create a local instance of Discourse
and then link it to your local KinesinLMS instance.

This is a pain, and of all the third-party services we use, Discourse is the only one that maybe should
be replaced with a local implementation like [django-machina](https://django-machina.readthedocs.io/en/latest/).

But the process is not too bad of a process if you use Docker.

The following instructions are for docker on macOS...see the Discourse forum for other options.

Note that once you have Discourse running locally in docker, you'll need to create a new user account and link the
Discourse instance to your KinesinLMS instance. (This same configuration process needs to happen when linking a live
Discourse instance to KinesinLMS staging or production instance.)

## Set Up Discourse Using Docker

The following steps describe how you would set up Discourse for local development, using Docker.

Discourse has a guide to setting up via Docker
here : https://meta.discourse.org/docs?category=56&tags=dev-install&topic=102009

The steps described there are listed below, but the Discourse page is likely more up to date, so check there first.

First clone our fork of the Discourse repo to your local machine. We made one change to the `boot_dev` script
to avoid an error when building the container when building on macOS. See the notes below for more info.

```
    git clone https://github.com/danielmcquillen/discourse.git
```

From there, `cd` into the newly created `discourse` the directory (cloned from GitHub repo).

Then, rely on a second hack (sigh) to avoid errors when building the container. Follow the
steps [noted here](https://meta.discourse.org/t/install-discourse-for-development-using-docker/102009/284)
to create your own Discourse Docker container and resolve Node upgrade issues in the base Docker container for
Discourse. Build that new container:

```
docker build -t discourse_node20 - < Dockerfile
```

Now you can run the base commands to establish the container per the Discourse instructions
in [this post](https://meta.discourse.org/t/install-discourse-for-development-using-docker/102009/252)
This does a one-time setup of the docker container ( via their symlink d -> /bin/docker ).

```
    d/boot_dev --init
```

At the end of the `boot_dev` process, you'll be asked to create an admin user. Do that, giving it the same
username as your superuser on the KinesinLMS instance you'll be linking to Discourse. For me, that user is `daniel`.
Make sure to grant Admin privileges to the account when prompted. The process will look something like this:

```
    14:35 $ ./bin/docker/rake admin:create
    Email:  daniel@mcquilleninteractive.com

    Ensuring account is active!

    Account updated successfully!
    Do you want to grant Admin privileges to this account? (Y/n)  y

    Your account now has Admin privileges!
```

Once the container is set up, anytime you want to run the container, run the following command ::

First terminal ::

```
    d/rails s
```

Second terminal ::

```
    d/ember-cli
```

This runs the server on localhost:9292 ::

```
    http://localhost:4200/
```

IMPORTANT: Make sure to check notes in docs about steps you might need to do after the init step (e.g. migrations).

https://meta.discourse.org/t/beginners-guide-to-install-discourse-for-development-using-docker/102009

## Connecting KinesinLMS to Discourse Locally

In the above step you should have created a new user in Discourse with the same username as your admin
user in KinesinLMS. For me, that user is `daniel`.

You're now ready to connect KinesinLMS to Discourse. This is the same process regardless of whether
you're running locally on in staging or production. Read on for details.

## Set up the Forum Provider

In KinesinLMS, go to Managment and click "Configure" in the Forum Provider card.

The only way you can use this form is if you've set up the `FORUM_API_KEY` and `FORUM_SSO_SECRET` environment variables.
If you haven't, the form will warn you to do so before proceeding.

Make sure the "Active" checkbox at the top of the form is checked.

For Forum url, enter `http://localhost:4200/` (or whatever the url is for your Discourse instance running in Docker)

For Forum API username, enter the username of your admin user in KinesinLMS, which should be the same as what you used
to create your admin in Discourse docker.




