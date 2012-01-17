"""Handles packaging, distribution, and testing."""


from setuptools import setup
from setuptools import find_packages


setup(

	# Basic package information.
	name = 'pyagi',
	version = '0.1',
	packages = find_packages(),

	# Packaging options.
	zip_safe = False,
	include_package_data = True,

	# Package dependencies.
	install_requires = [],
	tests_require = [],

	# Metadata for PyPI.
	author = 'Randall Degges',
	author_email = 'rdegges@gmail.com',
	license = 'UNLICENSE',
    url = 'https://github.com/rdegges/pyagi',
	keywords = 'asterisk agi application gateway interface telephony voip',
	description = 'An Asterisk AGI library for humans.',
	long_description = open('README').read(),

)
