from setuptools import Extension, find_packages, setup

# TODO: figure out how to run npm run build
setup(
    name="cowboy-client",
    version="0.7.1",
    packages=find_packages(),
    description="Cowboy Client Interface",
    # long_description=long_description,
    # long_description_content_type="text/markdown",
    author="John Peng",
    author_email="kongyijipeng@gmail.com",
    install_requires=[
        "click",
        "pyyaml",
        "pydantic==2.7.4",
        "gitpython==3.0.6",
        "requests",
        "platformdirs",
        "pytz",
    ],
    entry_points={
        "console_scripts": [
            "cowboy = cowboy.cli:entrypoint",
        ],
    },
    python_requires=">=3.8",
    include_package_data=True,
    exclude_package_data={
        "": ["static/*"],
    },
)
