# Vertretungsplan App - Setup Anleitung

Diese App zeigt den Vertretungsplan vom Kranich-Gymnasium an, gefiltert nach Klasse.

## 📁 Dateien

- `backend.py` - Python Backend Server (holt Daten von IServ)
- `requirements.txt` - Python Abhängigkeiten
- `vertretungsplan-app.html` - Frontend PWA (Progressive Web App)

## 🚀 Installation & Start

### Schritt 1: Python Backend installieren

```bash
# Python-Pakete installieren
pip install -r requirements.txt

# Backend starten
python backend.py
```

Das Backend läuft jetzt auf `http://localhost:5000`

### Schritt 2: Frontend öffnen

Öffne einfach `vertretungsplan-app.html` in deinem Browser!

- Auf dem PC: Doppelklick auf die Datei
- Oder: Mit einem lokalen Webserver (z.B. `python -m http.server 8000`)

## 📱 Als App auf dem Handy nutzen

### Option A: Lokales Netzwerk (am einfachsten)

1. Stelle sicher, dass dein Handy und PC im gleichen WLAN sind
2. Finde die IP-Adresse deines PCs:
   - Windows: `ipconfig` im CMD
   - Mac/Linux: `ifconfig` oder `ip addr`
3. Öffne auf dem Handy: `http://DEINE-PC-IP:8000/vertretungsplan-app.html`
4. Speichere die Seite als App (siehe unten)

### Option B: Online hosten (für alle zugänglich)

Du kannst das Backend kostenlos hosten auf:

**Render.com (empfohlen):**
1. Gehe zu https://render.com
2. Erstelle ein neues "Web Service"
3. Verbinde dein Git-Repository oder upload die Dateien
4. Render erkennt automatisch die `requirements.txt`
5. Setze Start-Command: `python backend.py`
6. Deploy!

**Railway.app:**
1. Gehe zu https://railway.app
2. "New Project" → "Deploy from GitHub"
3. Upload deine Dateien
4. Railway deployed automatisch

**PythonAnywhere.com:**
- Kostenloser Account für kleine Projekte
- Upload Dateien und starte die Flask-App

### Frontend hosten:

Hoste die `vertretungsplan-app.html` auf:
- **Netlify** (kostenlos, einfach Drag & Drop)
- **Vercel** (kostenlos)
- **GitHub Pages** (kostenlos)

**WICHTIG:** Wenn Backend und Frontend auf verschiedenen Domains laufen, musst du im Frontend die Backend-URL anpassen:

In `vertretungsplan-app.html` ändere:
```javascript
const response = await fetch('http://localhost:5000/api/check', {
```
zu:
```javascript
const response = await fetch('https://dein-backend-url.com/api/check', {
```

## 📲 Als App auf Homescreen speichern

### iPhone (iOS):
1. Öffne die Website in Safari
2. Tippe auf das "Teilen" Icon (Quadrat mit Pfeil)
3. Scrolle runter und wähle "Zum Home-Bildschirm"
4. Gib einen Namen ein (z.B. "Vertretungsplan")
5. Tippe "Hinzufügen"

### Android:
1. Öffne die Website in Chrome
2. Tippe auf die drei Punkte (⋮) oben rechts
3. Wähle "Zum Startbildschirm hinzufügen"
4. Gib einen Namen ein
5. Tippe "Hinzufügen"

Die App öffnet sich jetzt im Vollbild wie eine echte App!

## 🔧 Anpassungen

### IServ-Zugangsdaten ändern

In `backend.py` (Zeile 10-11):
```python
ISERV_USERNAME = "dein.benutzername"
ISERV_PASSWORD = "deinPasswort"
```

### Design anpassen

Die Farben kannst du in `vertretungsplan-app.html` ändern (Zeile 18-27):
```css
:root {
    --bg-primary: #0f172a;      /* Haupt-Hintergrund */
    --accent-primary: #3b82f6;  /* Haupt-Akzentfarbe */
    --accent-secondary: #8b5cf6; /* Zweite Akzentfarbe */
    /* ... */
}
```

## 🐛 Troubleshooting

**"Fehler beim Abrufen des Vertretungsplans"**
- Prüfe ob das Backend läuft (`python backend.py`)
- Prüfe die Console im Browser (F12) für Fehler
- Stelle sicher, dass die Backend-URL korrekt ist

**"Login bei IServ fehlgeschlagen"**
- Prüfe Benutzername und Passwort in `backend.py`
- IServ könnte ein CAPTCHA haben - dann manuell im Browser einloggen

**"Keine Einträge gefunden"**
- Das HTML-Format von IServ könnte sich geändert haben
- Prüfe die IServ-Webseite manuell
- Eventuell muss der Parser in `backend.py` angepasst werden

## 🔒 Sicherheit

**WICHTIG:** Deine IServ-Zugangsdaten stehen im Backend-Code!

Wenn du das öffentlich hosted:
- Nutze Umgebungsvariablen statt Hardcoded Credentials
- Setze die Credentials auf deinem Hosting-Service (Render/Railway)

Beispiel für Umgebungsvariablen:
```python
import os

ISERV_USERNAME = os.getenv('ISERV_USERNAME', 'fallback_username')
ISERV_PASSWORD = os.getenv('ISERV_PASSWORD', 'fallback_password')
```

## 📊 Funktionsweise

1. User gibt Klasse ein (z.B. "11D")
2. Frontend sendet Request an Backend
3. Backend loggt sich bei IServ ein
4. Backend lädt Vertretungsplan-Seite
5. Backend parst HTML und filtert nach Klasse
6. Backend sendet Ergebnisse zurück
7. Frontend zeigt schön formatiert an

## 💡 Ideen für Erweiterungen

- [ ] Push-Benachrichtigungen bei neuen Änderungen
- [ ] Stundenplan speichern und nur relevante Fächer anzeigen
- [ ] Teilen-Funktion für Klassenkameraden
- [ ] Wochenübersicht
- [ ] Export als Kalender-Datei (.ics)
- [ ] Dark/Light Mode Toggle

## 📞 Support

Bei Fragen oder Problemen, check die Browser-Console (F12) für Error-Messages!

Viel Erfolg! 🚀
