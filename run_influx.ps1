# Konfiguration — Standardwerte (systemunabhaengig)
$projectDir  = $PSScriptRoot
$influxPort  = 8181
$startupWait = 30

# Lokale Konfiguration laden (systemspezifische Pfade, nicht im Git)
$localConfig = Join-Path $PSScriptRoot "run_influx_local.ps1"
if (Test-Path $localConfig) {
    . $localConfig
} else {
    Write-Host "FEHLER: run_influx_local.ps1 nicht gefunden."
    Write-Host "Bitte run_influx_local.example.ps1 kopieren, umbenennen und Pfade anpassen."
    exit 1
}

$logFile = "$projectDir\logs\influx_pipeline.log"

# Logging
function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp  $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

# InfluxDB Port-Check
function Test-InfluxDB {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("localhost", $influxPort)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

# Logs-Ordner erstellen falls nicht vorhanden
if (-not (Test-Path "$projectDir\logs")) {
    New-Item -ItemType Directory -Path "$projectDir\logs" | Out-Null
}

Write-Log "========================================================"
Write-Log "Pipeline gestartet"

# InfluxDB starten falls nicht aktiv
if (Test-InfluxDB) {
    Write-Log "InfluxDB laeuft bereits auf Port $influxPort."
} else {
    Write-Log "InfluxDB nicht erreichbar - starte influxdb3.exe..."
    Start-Process -FilePath $influxExe -WindowStyle Normal

    $elapsed = 0
    while (-not (Test-InfluxDB) -and $elapsed -lt $startupWait) {
        Start-Sleep -Seconds 2
        $elapsed += 2
    }

    if (Test-InfluxDB) {
        Write-Log "InfluxDB erfolgreich gestartet (nach ${elapsed}s)."
    } else {
        Write-Log "FEHLER: InfluxDB konnte nach ${startupWait}s nicht gestartet werden. Pipeline abgebrochen."
        exit 1
    }
}

# Influx.py ausfuehren
Set-Location $projectDir
Write-Log "Starte Influx.py..."

$output = & $pythonExe "$projectDir\Influx.py" 2>&1
$exitCode = $LASTEXITCODE

$output | ForEach-Object { Write-Log $_ }

if ($exitCode -eq 0) {
    Write-Log "Influx.py erfolgreich abgeschlossen (Exit-Code 0)."
} else {
    Write-Log "FEHLER: Influx.py mit Exit-Code $exitCode beendet."
}

Write-Log "Pipeline beendet"
Write-Log "========================================================"
