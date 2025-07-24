@echo off
REM Parameterized PyPI Publishing Script
REM Usage: publish-to-pypi.bat [drive] [directory] [build_name] [exe_name]
REM Example: publish-to-pypi.bat d d:/dev2/whitelistmcp2 whitelistmcp_mcp whitelistmcp

setlocal EnableDelayedExpansion

REM Set default values if parameters not provided
set DRIVE=%~1
set DIRECTORY=%~2
set BUILD_NAME=%~3
set EXE_NAME=%~4

REM Use defaults if parameters are empty
if "%DRIVE%"=="" set DRIVE=d
if "%DIRECTORY%"=="" set DIRECTORY=d:/dev2/whitelistmcp2
if "%BUILD_NAME%"=="" set BUILD_NAME=whitelistmcp_mcp
if "%EXE_NAME%"=="" set EXE_NAME=whitelistmcp

echo ========================================
echo PyPI Publishing Script
echo ========================================
echo Drive: %DRIVE%
echo Directory: %DIRECTORY%
echo Build Name: %BUILD_NAME%
echo Executable Name: %EXE_NAME%
echo ========================================

REM Load PyPI environment variables
echo Loading PyPI credentials...
if exist "%~dp0PyPi.env" (
    for /f "tokens=1,2 delims==" %%a in ('type "%~dp0PyPi.env" ^| findstr /v "^#" ^| findstr /v "^$"') do (
        set "%%a=%%b"
    )
    echo PyPI credentials loaded successfully
) else (
    echo ERROR: PyPi.env file not found!
    echo Please ensure PyPi.env exists in the same directory as this script
    exit /b 1
)

REM Change to the specified drive
echo.
echo Changing to drive %DRIVE%:
%DRIVE%:

REM Change to the project directory
echo Changing to directory %DIRECTORY%
cd %DIRECTORY%

REM Clean previous builds
echo.
echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist %BUILD_NAME%.egg-info rmdir /s /q %BUILD_NAME%.egg-info
if exist dist rmdir /s /q dist

REM Build the package
echo.
echo Building package...
python -m build
if errorlevel 1 (
    echo ERROR: Build failed!
    exit /b 1
)

REM Upload to PyPI
echo.
echo Uploading to PyPI...
python -m twine upload dist/*
if errorlevel 1 (
    echo ERROR: Upload to PyPI failed!
    exit /b 1
)

REM Uninstall existing package
echo.
echo Uninstalling existing %BUILD_NAME% package...
python -m pip uninstall %BUILD_NAME% -y

REM Optional: Test the executable
echo.
echo Testing %EXE_NAME% executable...
where %EXE_NAME%.exe >nul 2>nul
if errorlevel 1 (
    echo WARNING: %EXE_NAME%.exe not found in PATH
    echo You may need to install the package: pip install %BUILD_NAME%
) else (
    echo %EXE_NAME%.exe found in PATH
    %EXE_NAME%.exe --version
)

echo.
echo ========================================
echo Publishing complete!
echo ========================================

endlocal