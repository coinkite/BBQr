#
# BBQr - Multi QR generation for Bitcoin stuff.
#

# To use this command, during dev, install and yet be able to edit the code:
#
#   pip install --editable .
#

from setuptools import setup

requirements = [
    'pyqrcode',
]

cli_requirements = [
    'click>=6.7',
]

tests_require = [
    'pytest'
]

with open("README.md", "r") as fh:
    long_description = fh.read()

from bbqr.version import __version__

setup(
    name='bbqr',
    version=__version__,
    packages=[ 'bbqr' ],
    python_requires='>3.8.0',
    install_requires=requirements,
    tests_require=tests_require,
    extras_require={
        'cli': cli_requirements,
    },
    url='https://github.com/Coldcard/BBQr',
    author='Coinkite Inc.',
    author_email='support@coinkite.com',
    description="Split data accross multiple QR codes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points='''
        [console_scripts]
        bbqr=bbqr.cli:main
    ''',
    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
    ],
)

