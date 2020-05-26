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

build: check-version unit-tests dist

dist: CHANGELOG.md setup.py
	rm -rf dist/
	python3 setup.py sdist bdist_wheel

upload: check-version unit-tests dist
	python3 -m twine upload dist/*

check-version: $(VERSION_LOCAL) $(VERSION_IN_PYPI)
	cat $(VERSION_LOCAL)
	grep -v `cat $(VERSION_LOCAL)` $(VERSION_IN_PYPI)
	grep -F "[`cat $(VERSION_LOCAL)`]" CHANGELOG.md

unit-tests:
	pytest --basetemp=".tmp/"

unit-tests-with-coverage:
	pytest -sv --cov=cincan tests --basetemp=".tmp/"

always-refresh:

$(VERSION_IN_PYPI): always-refresh
	mkdir -p $(dir $@)
	pip3 search "cincan" | grep "cincan-command" |  grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+" > $@
	cat $@

clean:
	rm -rf build dist cincan_command.egg-info


