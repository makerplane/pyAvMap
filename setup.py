import setuptools
import glob
import os

with open("README.rst", "r") as fh:
    long_description = fh.read()

datafiles = [('etc/fixgw', ['config/default.yaml', 'config/default.db', 'config/c170b.ini','config/fg_172.ini']),
             ('etc/fixgw/canfix', ['config/canfix/default.map']),
#             ('share/fixgw/doc', ['doc/_build/FIXGateway-html.tar.gz', 'doc/_build/latex/FIXGateway.pdf']),
             ('share/fixgw', ['fixgw/plugins/fgfs/fix_fgfs.xml']),
]

setuptools.setup(
    name="fixgw",
    version="0.1.0",
    author="Phil Birkelbach",
    author_email="phil@petrasoft.net",
    description="FIX-Gateway: Gateway software for the Flight Information eXchange protocols",
    long_description=long_description,
    #long_description_content_type="text/x-rst",
    url="https://github.com/makerplane/FIX-Gateway",
    packages=setuptools.find_packages(),
    #packages=['canfix'],
    #package_data = {'fixgw':['config/*']},
    install_requires = ['pyyaml',],
    data_files = datafiles,
    #test_suite = 'tests',
    #scripts = ['bin/fixgw', 'bin/fixgwc'],
    entry_points = {
        'console_scripts': ['fixgw=fixgw.server:main', 'fixgwc=fixgw.client:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)"
        "Operating System :: POSIX :: Linux",
    ],
    test_suite = 'tests',
)
