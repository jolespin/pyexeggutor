from setuptools import setup
import os

script_directory = os.path.abspath(os.path.dirname(__file__))

package_name = "pyexeggutor"
version = None
with open(os.path.join(script_directory, package_name, '__init__.py')) as f:
    for line in f.readlines():
        line = line.strip()
        if line.startswith("__version__"):
            version = line.split("=")[-1].strip().strip('"')
assert version is not None, f"Check version in {package_name}/__init__.py"

requirements = list()
with open(os.path.join(script_directory, 'requirements.txt')) as f:
    for line in f.readlines():
        line = line.strip()
        if line:
            if not line.startswith("#"):
                requirements.append(line)
                
setup(name='pyexeggutor',
    version=version,
    description='Run shell commands in Python',
    url='https://github.com/jolespin/pyexeggutor',
    author='Josh L. Espinoza',
    author_email='jol.espinoz@gmail.com',
    license='MIT',
    packages=["pyexeggutor", "pyexeggutor.cli"],
    install_requires=requirements,
    include_package_data=False,
    entry_points={
        "console_scripts": [
            "parse-time-v=pyexeggutor.cli.parse_time_v:main",
            "archive-subdirectories=pyexeggutor.cli.archive_subdirectories:main",
            "ftp-downloader=pyexeggutor.cli.ftp_downloader:main",
        ]
    },)

