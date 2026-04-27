# Lokale Konfiguration — systemspezifische Pfade
#
# Anleitung:
#   1. Diese Datei kopieren und als "run_influx_local.ps1" speichern
#   2. Die drei Pfade unten auf dein System anpassen
#   3. run_influx_local.ps1 wird nicht ins Git committed (gitignored)

# Pfad zum Python-Interpreter (Anaconda oder venv)
# Beispiele:
#   $pythonExe = "C:\Users\DEIN_BENUTZERNAME\anaconda3\python.exe"
#   $pythonExe = "C:\Users\DEIN_BENUTZERNAME\miniconda3\python.exe"
#   $pythonExe = "C:\DIFA_influxv3\.venv\Scripts\python.exe"
$pythonExe = "C:\Users\DEIN_BENUTZERNAME\anaconda3\python.exe"

# Pfad zur influxdb3.exe (Versionsnummer je nach installierter Version anpassen)
# Beispiel: "C:\Program Files\influxdb3-core-3.8.0-windows_amd64\influxdb3.exe"
$influxExe = "C:\Program Files\influxdb3-core-X.X.X-windows_amd64\influxdb3.exe"
