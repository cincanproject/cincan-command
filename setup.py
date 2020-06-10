from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as ver:
    version_info = ver.read().strip()

setup(
    name='cincan-command',
    version=version_info,
    author="Rauli Kaksonen",
    author_email="rauli.kaksonen@gmail.com",
    description='Cincan wrapper for dockerized command-line tools',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/cincan/cincan-command",
    packages=['cincan'],
    install_requires=['docker>=4.1', 'cincan-registry>=0.1.1'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['cincan=cincan.frontend:main'],
    },
    python_requires='>=3.6',
)
