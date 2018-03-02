"""setup."""
# pylint: disable=invalid-name, import-error
from setuptools import setup, find_packages
from pipenv.project import Project
from pipenv.utils import convert_deps_to_pip


# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

pfile = Project().parsed_pipfile
install_requires = convert_deps_to_pip(pfile['packages'], r=False)
tests_require = convert_deps_to_pip(pfile['dev-packages'], r=False)


setup(
    name='gbooru-images-download',
    description="Simple booru for hydrus",
    version="0.0.1",
    long_description=long_description,
    url="https://github.com/rachmadaniHaryono/gbooru-images-download",
    # uncomment if tarball is provided on github
    # download_url='https://github.com/"
    # "rachmadaniHaryono/google-images-download/tarball/' + __version__,
    license='MIT',
    zip_safe=True,

    install_requires=install_requires,
    setup_requires=['pytest-runner', 'pipenv'],
    tests_require=tests_require,
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
            'gbooru-images-download-server = gbooru_images_download.server:cli'
        ]},
)
