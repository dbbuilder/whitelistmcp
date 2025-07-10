"""Setup script for AWS Whitelisting MCP Server."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="awswhitelist",
    version="0.1.0",
    author="AWS Whitelisting Team",
    description="AWS Security Group IP Whitelisting MCP Server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbbuilder/awswhitelist2",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "awswhitelist=awswhitelist.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "awswhitelist": ["py.typed"],
    },
)