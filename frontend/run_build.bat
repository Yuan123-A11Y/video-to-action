@echo off
cd /d G:\trae\video-to-action\frontend
echo Running npm install...
call npm install > build_log.txt 2>&1
echo npm install exit code: %ERRORLEVEL% >> build_log.txt

echo Running npm run build...
call npm run build >> build_log.txt 2>&1
echo npm run build exit code: %ERRORLEVEL% >> build_log.txt

echo Build complete. Check build_log.txt for details.
type build_log.txt
