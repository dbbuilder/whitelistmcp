@echo off
REM Quick Start Script for AWS Security Group Whitelist Management
REM This script provides an easy way to run the most common operations

echo.
echo ===================================================
echo AWS Security Group Whitelist Management - Quick Start
echo ===================================================
echo.

:menu
echo Select an option:
echo 1. Test AWS Connectivity
echo 2. Add IP Rule (JSON method)
echo 3. View Example JSON Configuration
echo 4. Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto test_aws
if "%choice%"=="2" goto add_rule
if "%choice%"=="3" goto view_example
if "%choice%"=="4" goto end

echo Invalid choice. Please try again.
goto menu

:test_aws
echo.
echo Testing AWS connectivity...
python test_aws_access.py
echo.
pause
goto menu

:add_rule
echo.
echo Example JSON format:
echo {"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8080","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}
echo.
set /p json="Enter your JSON configuration: "
python add_sg_rule_json.py %json%
echo.
pause
goto menu

:view_example
echo.
echo Example JSON Configuration:
type example_config.json
echo.
echo.
pause
goto menu

:end
echo.
echo Thank you for using AWS Security Group Whitelist Management!
echo.