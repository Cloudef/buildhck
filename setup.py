#!/usr/bin/env python3

from setuptools import setup, find_packages
from setuptools.command.test import test

class PyTest(test):
    def initialize_options(self):
        super().initialize_options()
        self.pytest_args = []

    def finalize_options(self):
        super().finalize_options()
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)

class PyLint(PyTest):
    def initialize_options(self):
        super().initialize_options()
        self.pytest_args = ['--pylint', '--ignore=tests']

setup(
    name='buildhck',
    url='https://github.com/Cloudef/buildhck',
    maintainer='Buildhck Team',
    include_package_data=True,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'buildhckc = buildhck.client.client:main'
        ]
    },
    tests_require=['pytest'],
    cmdclass={
        'test': PyTest,
        'lint': PyLint
    }
)
