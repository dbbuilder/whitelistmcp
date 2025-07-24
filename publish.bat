@echo off
REM Quick publish script with defaults for whitelistmcp project

echo Publishing whitelistmcp to PyPI...
call "%~dp0publish-to-pypi.bat" d d:/dev2/whitelistmcp3 whitelistmcp whitelistmcp