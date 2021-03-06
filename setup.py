#!/usr/bin/env python2
# coding: utf-8
from setuptools import setup, find_packages
from twitterlib import __author__, __version__, __license__
 
setup(
    name = 'twitterlib',
    version = __version__,
    description = '1 file Twitter library for Python',
    license = __license__,
    author = __author__,
    author_email = 'darknesssharp@gmail.com',
    url = 'https://github.com/yatt/twitterlib.git',
    keywords = 'twitter python',
    packages = find_packages(),
    install_requires = [],
    )
