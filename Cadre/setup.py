# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from cadre import __version__

packages = find_packages()

setup(
    name="Cadre",
    version=__version__,
    description="""Cadre - a PictureFrame application based on the Coherence DLNA/UPnP framework""",
    author="Frank Scholz",
    author_email='fs@beebits.net',
    packages=packages,
    include_package_data = True,
    zipfile = None,
    scripts = ['bin/cadre'],
    url = "http://coherence-project.org",

    package_data = {
        'cadre': []
    },
)
