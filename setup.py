"""setup."""
# pylint: disable=invalid-name, import-error
from setuptools import setup, find_packages


# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

test_deps = [
    'flake8>=3.3.0',
    'mypy>=0.701',
    'pylint>=1.7.4',
    'pytest>=4.5.0',
    'tox>=2.7.0',
    'vcrpy>=1.11.1',
]
dev_deps = test_deps + [
    'flask-shell-ipython>=0.3.0',
]

setup(
    name='gbooru-images-download',
    description="Simple booru for hydrus",
    version="0.1.0",
    long_description=long_description,
    url="https://github.com/rachmadaniHaryono/gbooru-images-download",
    # uncomment if tarball is provided on github
    # download_url='https://github.com/"
    # "rachmadaniHaryono/google-images-download/tarball/' + __version__,
    license='MIT',
    zip_safe=True,
    install_requires=[
        'appdirs>=1.4.3',
        'beautifulsoup4>=4.7.1',
        'Click>=7.0',
        'fake-useragent>=0.1.11',
        'Flask-Admin>=1.5.3',
        'Flask-Migrate>=2.5.2',
        'Flask-SQLAlchemy>=2.4.0',
        'Flask-WTF>=0.14.2',
        'Flask>=1.0.3',
        'furl>=2.0.0',
        'humanize>=0.5.1',
        'lxml>=4.3.3',
        'Pillow>=6.0.0',
        'requests-html>=0.10.0',
        'requests>=2.22.0',
        'SQLAlchemy-Utils>=0.33.11',
        'SQLAlchemy>=1.3.4',
    ],
    tests_require=test_deps,
    extras_require={
        'test': test_deps,
        'dev': dev_deps,
    },
    setup_requires=['pytest-runner'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python',
    ],
    keywords="booru hydrus image downloader",
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Rachmadani Haryono',
    author_email="foreturiga@gmail.com",
    entry_points={
        'console_scripts': [
            'gbooru-images-download = gbooru_images_download.__main__:cli'
        ]},
)
