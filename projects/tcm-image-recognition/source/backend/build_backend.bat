@echo off
rem This is a batch script for packaging the production backend.

rem Set the project root directory (the directory where the script is located)
set "PROJECT_DIR=%~dp0"
rem Set the path to the virtual environment (relative to the project directory)
set "VENV_PATH=%PROJECT_DIR%venv311"

rem --- Step 1: Activate the virtual environment ---
echo [INFO] Activating Python virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment. Please check the path in VENV_PATH.
    goto :eof
)

echo [INFO] Virtual environment activated.

rem --- Step 2: Clean up old build artifacts ---
rem To ensure a clean build, delete previously generated build and dist folders.
echo [INFO] Cleaning up old build artifacts...
if exist "%PROJECT_DIR%build" (
    echo [INFO] Removing old build directory...
    rd /s /q "%PROJECT_DIR%build"
)
if exist "%PROJECT_DIR%dist" (
    echo [INFO] Removing old dist directory...
    rd /s /q "%PROJECT_DIR%dist"
)

echo [INFO] Cleanup complete.

rem --- Step 3: Package with PyInstaller ---
rem We use the build_prod.spec file, which is optimized for the production environment.
echo [INFO] Starting PyInstaller build process...
rem --noconfirm will automatically overwrite the old output, but we have already manually cleaned it up above.
pyinstaller --noconfirm build.spec

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed. Please check the output above for errors.
    goto :eof
)

echo.
echo [SUCCESS] Backend packaging completed successfully!
echo The final application is located in: %PROJECT_DIR%dist\tcm_app

rem 增加 pause 命令，以便在出错时能看到控制台输出
pause

