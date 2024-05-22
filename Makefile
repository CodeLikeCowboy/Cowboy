make:
	rm -rf dist
	rm -rf cowboy.egg-info
	python -m build .

	# switch over to the release version of the config
	sed "s/^CLIENT_MODE = \".*\"/CLIENT_MODE = \"release\"/" cowboy/config.py

upload-test:
	python -m twine upload --repository pypitest dist/*

upload-prod:
	python -m twine upload --repository pypi dist/*