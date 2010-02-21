# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from mirabeau import __version__


"""
dependencies:

- python-gst0.10
- python-dbus
- python-hildon
- python-gtk2
- python-telepathy
- python-pkg-resources
- python-setuptools
- python-twisted
"""

packages = find_packages()

setup(
    name="Mirabeau",
    version=__version__,
    description="FILL ME",
    long_description="""I make coffee too.
""",
    author="Philippe Normand and Frank Scholz",
    author_email='coherence@beebits.net',
    license = "MIT",
    packages=packages,
    scripts = ['bin/mirabeau'],
    url = "http://coherence-project.org/wiki/Mirabeau",
    download_url = 'http://coherence-project.org/download/Mirabeau-%s.tar.gz' % __version__,
    keywords=['UPnP', 'DLNA'],
    classifiers = ['Development Status :: 4 - Beta',
                   'Environment :: X11 Applications :: GTK',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                ],

    package_data = {
        'mirabeau': ['data/icons/*.png'],
    },
    install_requires=[
    'Coherence >= 0.6.7',
    ]
)
