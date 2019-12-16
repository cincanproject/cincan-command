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

VERSION_LOCAL = build/version-local

VERSION_IN_PYPI = build/version-in-pip

build: check-version dist

dist:
	python3 setup.py sdist bdist_wheel

upload: check-version dist
	python3 -m twine upload dist/*

check-version: $(VERSION_LOCAL) $(VERSION_IN_PYPI)
	cat $(VERSION_LOCAL)
	grep -v `cat $(VERSION_LOCAL)` $(VERSION_IN_PYPI)
	grep -F "[`cat $(VERSION_LOCAL)`]" CHANGELOG.md

$(VERSION_LOCAL): setup.py
	mkdir -p $(dir $@)
	grep "version.*=" setup.py |  grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+" > $@
	cat $@

always-refresh:

$(VERSION_IN_PYPI): always-refresh
	mkdir -p $(dir $@)
	pip3 search "cincan" | grep "cincan-command" |  grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+" > $@
	cat $@

clean:
	rm -rf build dist cincan_command.egg-info


