# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from cadre import __version__

packages = find_packages()

long_description = "\n\n".join([
    open("README.txt").read(),
    ])

setup(
    name="Cadre",
    version=__version__,
    description="""A DLNA/UPnP-PictureFrame application based on the Coherence framework""",
    long_description = long_description,
    author="Frank Scholz",
    author_email='fs@beebits.net',
    license = "MIT",
    packages=packages,
    include_package_data = True,
    zipfile = None,
    scripts = ['bin/cadre'],
    url = "http://coherence-project.org",
    classifiers = [
        #'Development Status :: 5 - Production/Stable',
        #'Environment :: Console',
        #'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        ]
    )
