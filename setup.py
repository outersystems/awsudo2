#!/usr/bin/env python

from setuptools import setup

setup(
    name='awsudo2',
    description='sudo-like utility to manage AWS credentials',
    url='https://github.com/outersystems/awsudo2',
    packages=['awsudo2'],
    entry_points={
        'console_scripts': [
            'awsudo2 = awsudo2.main:main',
        ],
    },
    install_requires=[
        'boto',
        'retrying',
        'awscli',
        'pytz==2019.3',
        'boto3==1.12.21'
    ],
)
