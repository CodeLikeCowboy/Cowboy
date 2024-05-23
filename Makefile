.PHONY: clean build install-local upload-test upload-prod

# Attempt to find python executable, prefer python3 if available
PYTHON := $(shell which python3 || which python)

clean:
	rm -rf dist
	rm -rf cowboy.egg-info

build: clean
	$(PYTHON) -m build .

	# switch over to the release version of the config
	sed "s/^CLIENT_MODE = \".*\"/CLIENT_MODE = \"release\"/" cowboy/config.py

install-local: build
	rm -rf ~/package/cowboy
	pip install --target ~/package/cowboy dist/*.whl

	cp tests/init/user1.yaml ~/package/cowboy/.user
	cp tests/init/test.yaml ~/package/cowboy/test.yaml
	

upload-test: build
	$(PYTHON) -m twine upload --repository pypitest dist/*

upload-prod: build
	$(PYTHON) -m twine upload --repository pypi dist/*
