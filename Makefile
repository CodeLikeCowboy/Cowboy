make:
	rm -rf dist
	rm -rf cowboy.egg-info
	python -m build .

upload-test:
	python -m twine upload --repository pypitest dist/*

upload-prod:
	python -m twine upload --repository pypi dist/*