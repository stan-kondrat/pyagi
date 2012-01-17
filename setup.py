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
	tests_require = ['nose>=1.1.2'],

	# Metadata for PyPI.
	author = 'Randall Degges',
	author_email = 'rdegges@gmail.com',
	license = 'UNLICENSE',
    url = 'https://github.com/rdegges/pyagi',
	keywords = 'asterisk agi application gateway interface telephony voip',
	description = 'An Asterisk AGI library for humans.',
	long_description = open('README').read(),
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'License :: Public Domain',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Communications :: Telephony',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

)
