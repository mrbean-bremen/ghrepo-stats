#!/usr/bin/env python
import os

from setuptools import setup, find_packages

from ghrepo_stats import __version__

EXTRA = {}

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(BASE_PATH, 'README.md')) as f:
    long_description = f.read()


setup(
    name="ghrepo-stats",
    packages=find_packages(),
    include_package_data=True,
    version=__version__,
    install_requires=["pygithub", "matplotlib"],
    description="Command line tools for GitHub repo statistics",
    author="mrbean-bremen",
    author_email="hansemrbean@googlemail.com",
    url="http://github.com/mrbean-bremen/ghrepo-stats",
    keywords="github python",
    license="MIT",
    entry_points={
        'console_scripts': [
            'show-ghstats=ghrepo_stats.show_gh_stats:main',
        ]
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        'Operating System :: MacOS',
        "Operating System :: Microsoft :: Windows",
        "Topic :: Utilities",
    ],
    long_description=long_description,
    long_description_content_type='text/markdown'
)
