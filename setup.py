"""Setup script for Multi-Cloud Whitelisting MCP Server."""

from setuptools import setup, find_packages
import os

# Read version
version = {}
with open("awswhitelist/__version__.py") as fp:
    exec(fp.read(), version)

# Read long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
requirements = []
if os.path.exists("requirements.txt"):
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    # Fallback to hardcoded requirements if file doesn't exist
    requirements = [
        # Common dependencies
        "python-json-logger>=2.0.7",
        "pydantic>=2.5.0",
        "requests>=2.28.0",
        # AWS dependencies
        "boto3>=1.34.0",
        "botocore>=1.34.0",
        # Azure dependencies
        "azure-identity>=1.15.0",
        "azure-mgmt-network>=25.0.0",
        "azure-core>=1.29.0",
        # GCP dependencies
        "google-cloud-compute>=1.14.0",
        "google-auth>=2.25.0",
    ]

setup(
    name="whitelistmcp",
    version=version["__version__"],
    author="DBBuilder",
    author_email="dbbuilderio@gmail.com",
    description="Multi-cloud MCP server for security group/firewall IP whitelisting across AWS, Azure, and GCP",
    keywords="aws, azure, gcp, security-group, firewall, nsg, mcp, model-context-protocol, whitelist, ip-management, multi-cloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbbuilder/whitelistmcp",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Security",
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
    extras_require={
        "remote": [
            "aiohttp>=3.8.0",
            "aiohttp-cors>=0.7.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "awswhitelist=awswhitelist.main:main",
            "awswhitelist-remote=awswhitelist.remote_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "awswhitelist": ["py.typed"],
    },
)