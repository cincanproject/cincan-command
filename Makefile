#
# Makefile for building cincan-command
#
# Main targets:
#
# build            Run setup.py to build distribution packages
#
# upload           Upload new version to PyPI
#
# clean            Clean the build
#
# Note, we check that version has been upgraded from one in PyPI
#

VERSION_LOCAL = VERSION

VERSION_IN_PYPI = build/version-in-pip

TESTENV_DIR = "_testenv"

TWINE_USERNAME = ${TWINE_USER} 

TWINE_PASSWORD = ${TWINE_PASS}

build: check-version tests dist

dist: CHANGELOG.md setup.py
	rm -rf dist/
	python3 setup.py sdist bdist_wheel

upload: check-version tests dist
	twine upload -r pypi dist/*

only-upload: check-version dist
	twine upload -r pypi dist/*

check-version: $(VERSION_LOCAL) $(VERSION_IN_PYPI)
	cat $(VERSION_LOCAL)
	grep -v `cat $(VERSION_LOCAL)` $(VERSION_IN_PYPI)
	grep -F "[`cat $(VERSION_LOCAL)`]" CHANGELOG.md

unit-tests:
	pytest --basetemp=".tmp/"

unit-tests-with-coverage:
	pytest --cov=cincan tests --basetemp=".tmp/"

integration-tests:
	sh tests/basic_integration_tests.sh $(TESTENV_DIR) $(VERSION_LOCAL)

tests: unit-tests integration-tests

always-refresh:

$(VERSION_IN_PYPI): always-refresh
	mkdir -p $(dir $@)
	pip3 search "cincan" | grep "cincan-command" |  grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+" > $@
	cat $@

clean:
	rm -rf build dist cincan_command.egg-info

