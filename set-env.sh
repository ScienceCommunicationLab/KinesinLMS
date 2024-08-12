
# Use this file if you're using EnvFile for Pycharm to load env files.
#
# If you do, your .env file will be in the format
#     BLAH=BLEH
# not the format
#     export BLAH=BLEH
#
# Therefore, if you're working directly in the terminal, and want to load the .env
# file, you need to run this script like:
#
# > source set-env.sh

set -o allexport
source _envs/_local/django.env
set +o allexport
