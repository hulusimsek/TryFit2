@echo off
cd /d "%~dp0"
set "TRYFIT_WORKSPACE=%~dp0"
set "DOTNET_CLI_HOME=%~dp0.dotnet"
set "NUGET_PACKAGES=%~dp0.nuget\packages"
set "DOTNET_CLI_TELEMETRY_OPTOUT=1"
powershell -NoProfile -Command "try { $tryFitHealth=Invoke-RestMethod 'http://127.0.0.1:5187/api/health' -TimeoutSec 2; if($tryFitHealth.ready -and $tryFitHealth.localOnly) { exit 0 }; exit 1 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  start "" "http://127.0.0.1:5187"
  exit /b 0
)
echo TryFit Next: http://127.0.0.1:5187
echo Sayfayi tarayicinda ac. Kapatmak icin bu pencerede Ctrl+C kullan.
dotnet run --project "web\TryFit.Local\TryFit.Local.csproj" --no-launch-profile
pause
