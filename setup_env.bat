@echo off
REM AWS Security Group Management - Environment Setup Script
REM This script helps set up the environment configuration

echo.
echo ================================================
echo AWS Security Group Management - Environment Setup
echo ================================================
echo.

REM Check if .env exists
if exist .env (
    echo [!] .env file already exists.
    set /p overwrite="Do you want to overwrite it? (y/N): "
    if /i not "%overwrite%"=="y" (
        echo Setup cancelled.
        goto :end
    )
)

echo Creating .env file from template...
copy .env.example .env > nul

echo.
echo Please enter your AWS configuration:
echo.

REM Get AWS credentials
set /p aws_key="AWS Access Key ID [press Enter to keep default]: "
if not "%aws_key%"=="" (
    powershell -Command "(Get-Content .env) -replace 'AWS_ACCESS_KEY_ID=.*', 'AWS_ACCESS_KEY_ID=%aws_key%' | Set-Content .env"
)

set /p aws_secret="AWS Secret Access Key [press Enter to keep default]: "
if not "%aws_secret%"=="" (
    powershell -Command "(Get-Content .env) -replace 'AWS_SECRET_ACCESS_KEY=.*', 'AWS_SECRET_ACCESS_KEY=%aws_secret%' | Set-Content .env"
)

set /p aws_region="AWS Region [us-east-1]: "
if "%aws_region%"=="" set aws_region=us-east-1
powershell -Command "(Get-Content .env) -replace 'AWS_DEFAULT_REGION=.*', 'AWS_DEFAULT_REGION=%aws_region%' | Set-Content .env"

echo.
echo Security Group Configuration:
echo.

set /p sg_id="Default Security Group ID [press Enter to skip]: "
if not "%sg_id%"=="" (
    powershell -Command "(Get-Content .env) -replace 'DEFAULT_SECURITY_GROUP_ID=.*', 'DEFAULT_SECURITY_GROUP_ID=%sg_id%' | Set-Content .env"
)

echo.
echo Installing Python dependencies...
pip install python-dotenv boto3 mcp

echo.
echo ================================
echo Environment setup complete!
echo ================================
echo.
echo Next steps:
echo 1. Review and edit .env file if needed
echo 2. Test AWS connection: python simple_test\test_aws_access.py
echo 3. Configure MCP server in Claude Desktop
echo.

:end
pause