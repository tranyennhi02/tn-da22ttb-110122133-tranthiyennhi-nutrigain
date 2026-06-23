@echo off
setlocal
cd /d d:\DOANTOTNGHIEP\NutriGain

echo ============================================
echo Step 1: compileall backend/app
echo ============================================
.venv\Scripts\python.exe -m compileall backend/app
echo EXIT_CODE_1=%ERRORLEVEL%

echo.
echo ============================================
echo Step 2: py_compile tag_food_quality_fields.py
echo ============================================
.venv\Scripts\python.exe -m py_compile backend/scripts/tag_food_quality_fields.py
echo EXIT_CODE_2=%ERRORLEVEL%

echo.
echo ============================================
echo Step 3: smoke_recommender_system.py
echo ============================================
.venv\Scripts\python.exe scripts/smoke_recommender_system.py
echo EXIT_CODE_3=%ERRORLEVEL%

echo.
echo ============================================
echo Step 4: frontend npm run build
echo ============================================
cd frontend
npm.cmd run build
echo EXIT_CODE_4=%ERRORLEVEL%

echo.
echo ============================================
echo DONE
echo ============================================
