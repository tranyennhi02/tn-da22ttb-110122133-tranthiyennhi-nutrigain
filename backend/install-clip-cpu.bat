@echo off
REM Install PyTorch CPU-only for CLIP ingredient recognition
REM This is lighter and faster for local development

echo Installing PyTorch CPU-only for CLIP...
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo.
echo Installation complete!
echo You can now restart the backend to use CLIP ingredient recognition.
pause
