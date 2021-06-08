#!/bin/bash

set -e
set -o pipefail
set -u

SCRIPTS_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIRECTORY="$SCRIPTS_DIRECTORY/.."
TESTS_DIRECTORY="$ROOT_DIRECTORY/tests"

# Process the command line arguments.
POSITIONAL=()
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        --debug)
        export DEBUG=1
        shift
        ;;
        *)
        POSITIONAL+=("$1")
        shift
        ;;
    esac
done

pushd "$TESTS_DIRECTORY" > /dev/null
PIPENV_PIPFILE="${ROOT_DIRECTORY}/Pipfile" pipenv run python3 -m unittest discover --verbose
popd > /dev/null
