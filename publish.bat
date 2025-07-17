@echo off
REM Quick publish script with defaults for awswhitelist2 project

echo Publishing awswhitelist_mcp to PyPI...
call "%~dp0publish-to-pypi.bat" d d:/dev2/awswhitelist2 awswhitelist_mcp awswhitelist