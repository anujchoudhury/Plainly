@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Plainly - iPhone link

echo Keep the run.bat window open while you use this.
echo.

rem ---- make sure the app is actually running before opening a tunnel to it
curl -s -o nul -m 3 http://127.0.0.1:8000/api/config
if errorlevel 1 (
  echo Plainly isn't running on this computer yet.
  echo Double-click run.bat, wait until it says "Application startup complete", then run phone.bat again.
  pause
  goto :eof
)

rem ---- 1) cloudflared, forced over HTTP/2 so venue Wi-Fi that blocks UDP still works
set "CF="
where cloudflared >nul 2>&1 && set "CF=cloudflared"
if not defined CF if exist "%~dp0cloudflared.exe" set "CF=%~dp0cloudflared.exe"
if not defined CF if exist "%ProgramFiles(x86)%\cloudflared\cloudflared.exe" set "CF=%ProgramFiles(x86)%\cloudflared\cloudflared.exe"
if not defined CF if exist "%ProgramFiles%\cloudflared\cloudflared.exe" set "CF=%ProgramFiles%\cloudflared\cloudflared.exe"
if not defined CF goto :ssh
echo Starting cloudflared. Look for a link ending in .trycloudflare.com in the box below,
echo type it into Safari on your iPhone, then tap Share and Add to Home Screen.
echo.
"%CF%" tunnel --protocol http2 --url http://127.0.0.1:8000
echo.
echo cloudflared stopped. Trying the no-install tunnel instead...
echo.

:ssh
rem ---- 2) Pinggy over the ssh that ships with Windows 10/11, on port 443 (rarely blocked)
where ssh >nul 2>&1 || goto :nossh
echo Opening a tunnel with Pinggy. If it asks for a password, just press Enter.
echo Use the https:// link it prints. If a "continue" page shows on the iPhone, tap through it once.
echo Press U to show a QR code you can scan with the iPhone camera.
echo.
ssh -p 443 -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -R0:127.0.0.1:8000 free.pinggy.io
echo.
echo Pinggy stopped. Trying localhost.run...
echo.
rem ---- 3) localhost.run over port 22
ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
pause
goto :eof

:nossh
echo This Windows has no ssh client. Install cloudflared with:
echo     winget install --id Cloudflare.cloudflared
echo or download cloudflared-windows-amd64.exe from https://github.com/cloudflare/cloudflared/releases/latest
echo rename it to cloudflared.exe, put it in this folder, and double-click phone.bat again.
pause
