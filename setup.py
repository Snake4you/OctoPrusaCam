# coding=utf-8
import sys

plugin_identifier = "octoprusacam"
plugin_package = "octoprint_octoprusacam"
plugin_name = "OctoPrusaCam"
plugin_version = "1.0.2"
plugin_description = "Bridge OctoPrint camera snapshots to Prusa Connect Camera API"
plugin_author = "Snake4you"
plugin_author_email = "snake4you@users.noreply.github.com"
plugin_url = "https://github.com/Snake4you/OctoPrusaCam"
plugin_license = "Apache-2.0"
plugin_requires = [
    "requests>=2.20.0",
    "Pillow>=6.2.0",
]

plugin_additional_data = []
plugin_additional_packages = []
plugin_ignored_packages = []
additional_setup_parameters = {}

try:
    import octoprint_setuptools
except ImportError:
    from setuptools import setup, find_packages

    setup_parameters = dict(
        name=plugin_name,
        version=plugin_version,
        description=plugin_description,
        author=plugin_author,
        author_email=plugin_author_email,
        url=plugin_url,
        license=plugin_license,
        packages=find_packages(),
        include_package_data=True,
        install_requires=plugin_requires,
        entry_points={
            "octoprint.plugin": [
                f"{plugin_identifier} = {plugin_package}"
            ]
        },
        python_requires=">=3.7,<4",
    )
else:
    setup_parameters = octoprint_setuptools.create_plugin_setup_parameters(
        identifier=plugin_identifier,
        package=plugin_package,
        name=plugin_name,
        version=plugin_version,
        description=plugin_description,
        author=plugin_author,
        mail=plugin_author_email,
        url=plugin_url,
        license=plugin_license,
        requires=plugin_requires,
        additional_packages=plugin_additional_packages,
        ignored_packages=plugin_ignored_packages,
        additional_data=plugin_additional_data,
    )

from setuptools import setup
setup(**setup_parameters)
