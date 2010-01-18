# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from cadre import __version__

packages = find_packages()

setup(
    name="Puncher",
    version=__version__,
    description="""Puncher - an UPNP InternetGatewayDevice manipulation tool based on Coherence DLNA/UPnP framework""",
    author="Frank Scholz",
    author_email='fs@beebits.net',
    packages=packages,
    include_package_data = True,
    zipfile = None,
    scripts = ['bin/puncher'],
    url = "http://coherence-project.org",

    package_data = {
        'puncher': []
    },
)
