# OctoPrusaCam

[![OctoPrint Plugin](https://img.shields.io/badge/OctoPrint-Plugin-blue.svg)](https://octoprint.org)
[![Python Version](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)
[![Release](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/Snake4you/OctoPrusaCam/releases)

**OctoPrusaCam** ist ein leichtgewichtiges OctoPrint-Plugin, das als direkte Bridge zwischen deiner in OctoPrint eingerichteten Webcam und der **Prusa Connect Camera API** dient.

Damit kannst du den Live-Snapshot-Feed deines Druckers nahtlos in der Prusa Connect Weboberfläche und der Prusa App anzeigen lassen – ohne separate Zusatzhardware, ohne Docker-Container und ohne komplexe Skripte.

---

## 🚀 Features

- 🔄 **Nahtlose Prusa Connect Integration:** Lädt periodisch Snapshots über den offiziellen Prusa Connect API-Endpunkt (`https://webcam.connect.prusa3d.com/c/snapshot`) per HTTP PUT hoch.
- ⚙️ **Umfangreiche Konfigurationsseite:** Integriert sich direkt in die OctoPrint-Einstellungen unter *Prusa Connect Cam*.
- 🔑 **Token- & Fingerprint-Verwaltung:** Sichere Eingabe des Prusa Connect Kamera-Tokens (mit Ein-/Ausblenden) und automatischer Fingerprint-Generator.
- 📷 **Automatische Webcam-Erkennung:** Verwendet standardmäßig die in OctoPrint konfigurierte Snapshot-URL (z.B. `/webcam/?action=snapshot` oder `http://127.0.0.1:8080/?action=snapshot`), unterstützt aber auch beliebige benutzerdefinierte URLs.
- 🧪 **Live-Test mit Vorschau:**
  - **Lokalen Snapshot testen:** Prüft, ob das Bild von der Kamera empfangen wird, und zeigt eine Miniatur-Vorschau an.
  - **Prusa Connect Upload testen:** Lädt sofort einen Test-Snapshot hoch und meldet den genauen HTTP-Statuscode (z.B. HTTP 200/204).
- ⏱️ **Einstellbares Intervall:** Upload-Intervall in Sekunden frei wählbar (Standard & Empfehlung von Prusa: **10 Sekunden**).
- 🛑 **"Nur während des Drucks"-Modus:** Pausiert den Bildupload automatisch, wenn der Drucker inaktiv ist, um Bandbreite und API-Calls zu sparen.
- 🔄 **Bildanpassung:** Drehung (0°, 90°, 180°, 270°) und Spiegelung (horizontal/vertikal) direkt vor dem Upload.
- 🔐 **HTTP Basic Auth:** Optionale Zugangsdaten für passwortgeschützte Webcam-Streams.
- 📊 **Statusanzeige:** Live-Status mit letztem Upload-Zeitstempel und HTTP-Meldung direkt im Einstellungsmenü.

---

## 📦 Installation

### Über den OctoPrint Plugin Manager (Empfohlen)

1. Öffne OctoPrint im Browser und gehe zu **Settings (Einstellungen)** &rarr; **Plugin Manager**.
2. Klicke auf **Get More... (Mehr anzeigen...)**.
3. Gib unter *... from URL* folgende URL ein:
   ```text
   https://github.com/Snake4you/OctoPrusaCam/archive/main.zip
   ```
4. Klicke auf **Install** und starte OctoPrint anschließend neu.

### Über die Kommandozeile (SSH / Virtualenv)

Melde dich via SSH auf deinem OctoPrint-Host (z.B. Raspberry Pi / OctoPi) an:

```bash
source ~/oprint/bin/activate
pip install "https://github.com/Snake4you/OctoPrusaCam/archive/main.zip"
sudo service octoprint restart
```

---

## 🛠️ Einrichtung & Anleitung

### 1. Kamera in Prusa Connect anlegen

1. Öffne [connect.prusa3d.com](https://connect.prusa3d.com) und wähle deinen Drucker aus.
2. Wechsle auf den Reiter **Kamera** (Camera).
3. Klicke auf **"+ Neue andere Kamera hinzufügen"** (*+ Add new other camera*).
4. Kopiere den dort generierten **Kamera-Token** (ein 20-stelliger Code).
5. *(Optional)* Falls dir ein Fingerprint angezeigt wird, kopiere auch diesen; andernfalls generiert OctoPrusaCam automatisch einen eindeutigen Fingerprint.

### 2. OctoPrusaCam konfigurieren

1. Öffne in OctoPrint die **Einstellungen** (Zahnrad-Symbol oben rechts).
2. Scrolle im linken Menü zum Bereich *Plugins* und wähle **Prusa Connect Cam**.
3. Aktiviere die Checkbox **"Prusa Connect Camera Bridge aktivieren"**.
4. Füge den kopierten **Kamera-Token** in das Token-Feld ein.
5. Das Feld **Snapshot-URL** kannst du leer lassen, falls deine OctoPrint-Webcam bereits normal funktioniert.
6. Klicke auf den Button **"Snapshot an Prusa Connect hochladen (Test)"**.
   - Du solltest ein grünes Erfolgsbanner mit Bildvorschau sehen.
7. Klicke unten rechts auf **Save (Speichern)**.
8. Fertig! In Prusa Connect wird dein Kamerabild nun alle 10 Sekunden automatisch aktualisiert.

---

## ⚙️ Konfigurationsoptionen

| Option | Typ | Standard | Beschreibung |
| :--- | :---: | :---: | :--- |
| **Prusa Connect Camera Bridge aktivieren** | Checkbox | `false` | Schaltet den automatischen Snapshot-Upload ein oder aus. |
| **Kamera Token** | Text | `""` | Der 20-stellige Authentifizierungs-Token von Prusa Connect. |
| **Fingerprint** | Text | *auto* | Eindeutige Kennung deiner Kamera (16 Hex-Zeichen). Kann per Klick neu generiert werden. |
| **Snapshot-URL** | Text | `""` | Snapshot-URL der Kamera. Leer lassen für OctoPrints Standard-Webcam. |
| **Kamera-Authentifizierung** | Text | `""` | Optionaler Benutzername & Passwort für Basic-Auth geschützte Streams. |
| **Bildausrichtung** | Auswahl | `0°` | Drehung (0°, 90°, 180°, 270°) sowie horizontale & vertikale Spiegelung. |
| **Upload-Intervall** | Zahl | `10` | Zeitabstand in Sekunden zwischen Snapshot-Uploads (Empfohlen: 10s). |
| **Nur während des Drucks hochladen**| Checkbox | `false` | Lädt Bilder nur hoch, wenn der Drucker druckt oder pausiert ist. |

---

## 🔍 Fehlerbehebung (Troubleshooting)

- **HTTP 401 / 403 (Unauthorized):**
  - Überprüfe den eingegebenen Kamera-Token.
  - Vergewissere dich, dass die Kamera in Prusa Connect nicht zwischenzeitlich gelöscht wurde.
- **Snapshot kann nicht abgerufen werden:**
  - Prüfe, ob deine Webcam in OctoPrint unter *Webcam & Zeitraffer* ein Bild liefert.
  - Wenn du eine externe IP-Kamera verwendest, trage die vollständige HTTP-Snapshot-URL (z.B. `http://192.168.1.50/snapshot.jpg`) ein.
- **Bild steht auf dem Kopf:**
  - Nutze die Ausrichtungs-Optionen (180° oder Spiegelung) direkt in den Plugin-Einstellungen.

---

## 📋 Kompatibilität

- **OctoPrint:** Version 1.4.0 oder neuer (vollständig getestet mit 1.9.x und 1.10.x)
- **Python:** Python 3.7 bis 3.12+ (Python 2 wird nicht unterstützt)
- **Plattform:** Beliebig (Raspberry Pi OS / OctoPi, Linux, macOS, Windows)

---

## 📄 Lizenz

Dieses Projekt ist unter der **Apache-2.0-Lizenz** lizenziert. Weitere Details findest du in der [LICENSE](LICENSE)-Datei.
