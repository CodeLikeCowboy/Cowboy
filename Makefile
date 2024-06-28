.PHONY: clean build install-local upload-test upload-prod

# Attempt to find python executable, prefer python3 if available
PYTHON := $(shell which python3 || which python)

clean:
	rm -rf dist
	rm -rf cowboy.egg-info

build: clean
	git submodule update --init --recursive
	
	cd static && npm run build && cd ..
	cp -r build cowboy

	$(PYTHON) -m build .

	# make sure that the config is set to release mode
	sed -i "s/^CLIENT_MODE = \".*\"/CLIENT_MODE = \"release\"/" cowboy/config.py

install-local: build
	rm -rf cowboy_local
	pip install --target cowboy_local dist/*.whl

	cp tests/init/user1.yaml cowboy_local/.user
	cp tests/init/test.yaml cowboy_local/test.yaml
	
upload-test: build
	$(PYTHON) -m twine upload --repository pypitest dist/*

upload-prod: build
	$(PYTHON) -m twine upload --repository pypi dist/*.whl
