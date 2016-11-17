from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='django-bitbucket-trello',
    version='0.0.8',
    description='Django Bitbucket & Trello Integration',
    long_description=long_description,
    url='https://github.com/relique/django-bitbucket-trello',
    author='Aldash Biibosunov',
    author_email='pythonista8@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities'
    ],
    keywords='bitbucket trello integration django',
    packages=['bitbucket_trello'],

    # Dependencies..
    install_requires=['requests>=2.11.1'],
    extras_require={},
    package_data={},
    data_files=[],
)
