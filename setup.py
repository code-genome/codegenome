#!/usr/bin/env python
from setuptools import find_namespace_packages, setup
from setuptools.command.develop import develop
from setuptools.command.install import install

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()


class PostInstallDependencies(install):
    def run(self):
        install.run(self)


setup(
    name="codegenome",
    version="0.0.1",
    description="Code Genome framework",
    url="https://research.ibm.com/",
    author="IBM Research",
    author_email="dkirat@us.ibm.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    packages=find_namespace_packages(include=["codegenome*"]),
    scripts=["scripts/cg"],
    python_requires=">=3.8",
    install_requires=requirements,
    mdclass={"install": PostInstallDependencies},
)
