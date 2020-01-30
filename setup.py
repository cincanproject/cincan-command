from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='cincan-command',
    version='0.2.6',
    author="Rauli Kaksonen",
    author_email="rauli.kaksonen@gmail.com",
    description='Cincan wrapper for dockerized command-line tools',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/cincan/cincan-command",
    packages=['cincan'],
    install_requires=['docker>=4.1'],
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
