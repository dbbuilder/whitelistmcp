"""Setup script for AWS Whitelisting MCP Server."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="awswhitelist-mcp",
    version="1.0.0",
    author="DBBuilder",
    author_email="dbbuilderio@gmail.com",
    description="MCP server for AWS Security Group IP whitelisting with stateless credential handling",
    keywords="aws, security-group, mcp, model-context-protocol, whitelist, ip-management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbbuilder/awswhitelist2",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
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