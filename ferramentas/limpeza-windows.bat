@echo off
setlocal
title Limpeza e Otimizacao do Windows

:: ============================================================
::  limpeza-windows.bat
::  Remove arquivos temporarios, caches e lixo do sistema
::  para liberar espaco e melhorar o desempenho do Windows.
::  Compativel com Windows 10 e 11.
:: ============================================================

:: --- Precisa rodar como Administrador: se nao estiver, pede elevacao ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de Administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "LOG=%USERPROFILE%\Desktop\limpeza-log.txt"
echo Limpeza iniciada em %date% %time% > "%LOG%"

:MENU
cls
echo ============================================================
echo            LIMPEZA E OTIMIZACAO DO WINDOWS
echo ============================================================
echo.
echo  Feche os navegadores e programas abertos antes de continuar.
echo.
echo  [1] Limpeza rapida   (temporarios, lixeira, caches, DNS)
echo  [2] Limpeza completa (rapida + Windows Update, reparo do
echo                        sistema e otimizacao do disco - demora)
echo  [3] Sair
echo.
choice /c 123 /n /m "Escolha uma opcao [1-3]: "
if errorlevel 3 goto FIM
if errorlevel 2 (set "MODO=COMPLETA") else (set "MODO=RAPIDA")

cls
echo Espaco livre ANTES da limpeza:
call :ESPACO_LIVRE
echo.

:: ------------------------------------------------------------
echo [1/9] Limpando arquivos temporarios do usuario...
call :LIMPAR_PASTA "%TEMP%"
call :LIMPAR_PASTA "%LOCALAPPDATA%\Temp"

echo [2/9] Limpando arquivos temporarios do Windows...
call :LIMPAR_PASTA "%SystemRoot%\Temp"

echo [3/9] Limpando relatorios de erro e despejos de memoria...
call :LIMPAR_PASTA "%ProgramData%\Microsoft\Windows\WER\ReportArchive"
call :LIMPAR_PASTA "%ProgramData%\Microsoft\Windows\WER\ReportQueue"
call :LIMPAR_PASTA "%LOCALAPPDATA%\CrashDumps"
call :LIMPAR_PASTA "%SystemRoot%\Minidump"
if exist "%SystemRoot%\MEMORY.DMP" del /f /q "%SystemRoot%\MEMORY.DMP" >nul 2>&1

echo [4/9] Limpando cache de miniaturas e icones...
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db" >nul 2>&1

echo [5/9] Limpando cache dos navegadores (historico e senhas sao mantidos)...
:: Google Chrome e Microsoft Edge (todos os perfis)
for %%B in ("Google\Chrome" "Microsoft\Edge" "BraveSoftware\Brave-Browser") do (
    if exist "%LOCALAPPDATA%\%%~B\User Data" (
        for /d %%P in ("%LOCALAPPDATA%\%%~B\User Data\*") do (
            call :LIMPAR_PASTA "%%P\Cache"
            call :LIMPAR_PASTA "%%P\Code Cache"
            call :LIMPAR_PASTA "%%P\GPUCache"
        )
    )
)
:: Mozilla Firefox (todos os perfis)
if exist "%LOCALAPPDATA%\Mozilla\Firefox\Profiles" (
    for /d %%P in ("%LOCALAPPDATA%\Mozilla\Firefox\Profiles\*") do (
        call :LIMPAR_PASTA "%%P\cache2"
    )
)

echo [6/9] Esvaziando a Lixeira...
powershell -NoProfile -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo [7/9] Limpando cache de DNS...
ipconfig /flushdns >nul 2>&1

echo [8/9] Limpando cache de Otimizacao de Entrega do Windows...
powershell -NoProfile -Command "Delete-DeliveryOptimizationCache -Force -ErrorAction SilentlyContinue" >nul 2>&1

echo [9/9] Executando a Limpeza de Disco do Windows (cleanmgr)...
call :CONFIGURAR_CLEANMGR
start /wait "" cleanmgr /sagerun:64

if "%MODO%"=="RAPIDA" goto RESULTADO

:: ------------------------------------------------------------
::  Etapas extras da limpeza completa
:: ------------------------------------------------------------
echo.
echo [Extra 1/4] Limpando cache de downloads do Windows Update...
net stop wuauserv >nul 2>&1
net stop bits >nul 2>&1
call :LIMPAR_PASTA "%SystemRoot%\SoftwareDistribution\Download"
net start bits >nul 2>&1
net start wuauserv >nul 2>&1

echo [Extra 2/4] Removendo versoes antigas de componentes do Windows (DISM)...
echo             Isso pode levar varios minutos.
DISM /Online /Cleanup-Image /StartComponentCleanup >> "%LOG%" 2>&1

echo [Extra 3/4] Verificando e reparando arquivos do sistema (SFC)...
echo             Isso pode levar varios minutos.
sfc /scannow >> "%LOG%" 2>&1

echo [Extra 4/4] Otimizando a unidade C: (TRIM em SSD / desfragmentacao em HD)...
defrag C: /O >> "%LOG%" 2>&1

:RESULTADO
echo.
echo ============================================================
echo Espaco livre DEPOIS da limpeza:
call :ESPACO_LIVRE
echo ============================================================
echo.
echo Limpeza concluida! Log salvo em:
echo   %LOG%
echo.
echo Recomendado: reinicie o computador para concluir a limpeza.
echo Limpeza concluida em %date% %time% >> "%LOG%"
echo.
choice /c SN /n /m "Deseja reiniciar agora? [S/N]: "
if errorlevel 2 goto FIM
shutdown /r /t 10 /c "Reiniciando apos a limpeza..."
goto FIM

:: ============================================================
::  Sub-rotinas
:: ============================================================

:: Apaga todo o conteudo de uma pasta, mantendo a pasta em si.
:: Arquivos em uso sao ignorados silenciosamente.
:: Trava de seguranca: so aceita caminhos completos (ex: C:\pasta) e
:: nunca a raiz de um disco, para evitar apagar algo por engano.
:LIMPAR_PASTA
if "%~1"=="" exit /b
set "ALVO=%~1"
if not "%ALVO:~1,2%"==":\" exit /b
if "%ALVO:~3%"=="" exit /b
if not exist "%ALVO%\" exit /b
echo    - %ALVO% >> "%LOG%"
del /f /s /q "%ALVO%\*" >nul 2>&1
for /d %%D in ("%ALVO%\*") do rd /s /q "%%D" >nul 2>&1
exit /b

:: Mostra o espaco livre da unidade C: em GB.
:ESPACO_LIVRE
powershell -NoProfile -Command "$d = Get-PSDrive C; '  Unidade C: {0:N2} GB livres de {1:N2} GB' -f ($d.Free/1GB), (($d.Free+$d.Used)/1GB)"
exit /b

:: Marca as categorias seguras da Limpeza de Disco para o perfil 64,
:: assim o cleanmgr roda sem precisar de interacao.
:CONFIGURAR_CLEANMGR
set "VC=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
for %%C in (
    "Active Setup Temp Folders"
    "Delivery Optimization Files"
    "Device Driver Packages"
    "Downloaded Program Files"
    "Internet Cache Files"
    "Old ChkDsk Files"
    "Setup Log Files"
    "System error memory dump files"
    "System error minidump files"
    "Temporary Files"
    "Temporary Setup Files"
    "Thumbnail Cache"
    "Update Cleanup"
    "Upgrade Discarded Files"
    "Windows Error Reporting Files"
    "Windows Upgrade Log Files"
) do (
    reg query "%VC%\%%~C" >nul 2>&1 && reg add "%VC%\%%~C" /v StateFlags0064 /t REG_DWORD /d 2 /f >nul 2>&1
)
exit /b

:FIM
endlocal
exit /b
