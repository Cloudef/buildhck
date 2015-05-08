#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='buildhck',
    url='https://github.com/Cloudef/buildhck',
    maintainer='Buildhck Team',
    include_package_data=True,
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'buildhckc = buildhck.client.client:main'
        ]
    }
)
