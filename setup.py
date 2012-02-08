'''
Created on Feb 8, 2012

@author: dannie
'''
from distutils.core import setup

setup(
    name='fdrasync',
    version='1.0',
    author='Dannie Chu',
    author_email='danb.chu AT gmail.com',
    packages=['fdrasync', 'fdrasync.management.commands'],
    license='LICENSE.txt',
    description='Django-based Asynchronous Jobs.',
    long_description=open('README.txt').read(),
    install_requires=[
        "Django >= 1.2",
        "beanstalkc",
    ],
)