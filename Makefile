.PHONY: clean build install-local upload-test upload-prod

clean:
	rm -rf dist
	rm -rf cowboy.egg-info

build: clean
	python -m build .

	# switch over to the release version of the config
	sed -i.bak "s/^CLIENT_MODE = \".*\"/CLIENT_MODE = \"release\"/" cowboy/config.py

install-local: build
	pip install --target ~/package/cowboy dist/*.whl

upload-test: build
	python -m twine upload --repository pypitest dist/*

upload-prod: build
	python -m twine upload --repository pypi dist/*
