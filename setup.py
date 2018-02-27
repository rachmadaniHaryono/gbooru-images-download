"""setup."""
from setuptools import setup, find_packages
from codecs import open
from os import path

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='google_images_download',
    version="0.3.1",
    description="Python Script to download hundreds of images from 'Google Images'. It is a ready-to-run code! ",
    long_description=long_description,
    url="https://github.com/rachmadaniHaryono/google-images-download",
    download_url='https://github.com/rachmadaniHaryono/google-images-download/tarball/' + __version__,
    license='MIT',
    zip_safe=True,

    install_requires=[
        'appdirs>=1.4.3',
        'beautifulsoup4>=4.6.0',
        'click>=6.7',
        'fake-useragent==0.1.7',
        'lxml>=4.0.0',
        'Pillow>=4.3.0',
        'requests>=2.14.2',
        'Send2Trash>=1.3.0',
        'structlog>=17.2.0',
    ],
    setup_requires=['pytest-runner', ],
    tests_require=['pytest', ],
    extras_require={
        'server': [
            'Flask-Admin>=1.5.0',
            'Flask-Bootstrap>=3.3.7.1',
            'flask-paginate==0.5.1',
            'Flask-Restless>=0.17.0',
            'Flask-SQLAlchemy>=2.3.1',
            'Flask-WTF>=0.14.2',
            'Flask>=0.12.2',
            'humanize>=0.5.1',
            'SQLAlchemy-Utils>=0.32.18',
        ],
    },
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
    keywords="google image downloader",
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    author='Hardik Vasa',
    author_email="hnvasa@gmail.com",
    entry_points={
        'console_scripts': [
            'googleimagesdownload = google_images_download.__init__:main'
            'google-images-download = google_images_download.__main__:cli',
            'google-images-download-server = google_images_download.server:cli'
        ]},

)
