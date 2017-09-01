#!/bin/bash
set -euo pipefail

# Current commit hash on the source branch.
SRC_BRANCH=master

# Switch to gh-pages branch.
git checkout gh-pages

# Get the YAML and the scripts we need to generate CSV and JSON
# from the source branch.
git fetch origin $SRC_BRANCH
HASH=$(git rev-parse origin/$SRC_BRANCH)
echo "Getting latest files from $SRC_BRANCH @ $HASH."
git checkout origin/$SRC_BRANCH *.yaml scripts

# Generate CSV and JSON.
(cd scripts/; python alternate_bulk_formats.py;)

# Commit the YAML, CSV, and JSON.
# (Don't commit the other scripts files we checked out from
# the source branch, which git has unhelpfully put in the
# index.)
export GIT_AUTHOR_NAME="the unitedstates project (CircleCI)"
export GIT_AUTHOR_EMAIL=circleci@theunitedstates.io
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="GIT_AUTHOR_EMAIL"
(
	git commit *.yaml *.csv *.json -m "update to $SRC_BRANCH @ $HASH by CircleCI" \
	&& git push
) || /bin/true # if there's nothing to commit, don't exit with error status

# Switch back to the original branch.
git checkout -f $SRC_BRANCH
