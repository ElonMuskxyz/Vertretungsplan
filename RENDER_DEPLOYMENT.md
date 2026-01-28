# 🚀 Deployment auf Render.com - Step by Step

## Vorbereitung

Du brauchst die **Cookie-Werte** aus deinem Browser. Hol sie dir aus Chrome DevTools (F12 → Application → Cookies):

- `IServSAT` → z.B. `eL5LYUJZkdlZXcH...`
- `IServSATId` → z.B. `6651d454-9427...`
- `IServSession` → z.B. `XagLHANcf5cj7c6...`

Kopiere die **kompletten Werte**!

---

## 📝 Schritt 1: Account erstellen

1. Gehe zu **https://render.com**
2. Klicke **"Get Started for Free"**
3. Registriere dich mit GitHub, GitLab oder Email
4. Bestätige deine Email

---

## 📂 Schritt 2: Dateien vorbereiten

Erstelle einen Ordner mit diesen Dateien:

```
vertretungsplan-backend/
├── backend_v5_production.py
└── requirements.txt
```

**requirements.txt** sollte enthalten:
```
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
beautifulsoup4==4.12.2
lxml==5.1.0
pypdf2==3.0.1
pdfplumber==0.10.3
```

---

## ☁️ Schritt 3: Backend auf Render deployen

### Option A: Mit GitHub (empfohlen)

1. **Erstelle ein GitHub Repository:**
   - Gehe zu https://github.com/new
   - Name: `vertretungsplan-backend`
   - Public oder Private
   - Create Repository

2. **Upload Dateien zu GitHub:**
   ```bash
   git init
   git add backend_v5_production.py requirements.txt
   git commit -m "Initial commit"
   git remote add origin https://github.com/DEIN-USERNAME/vertretungsplan-backend.git
   git push -u origin main
   ```

3. **In Render:**
   - Dashboard → **"New +"** → **"Web Service"**
   - **"Connect Repository"** → Wähle dein GitHub Repo
   - Settings:
     - **Name:** `vertretungsplan-backend`
     - **Region:** Frankfurt (Europe)
     - **Branch:** main
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `python backend_v5_production.py`
     - **Instance Type:** Free
   
4. **Environment Variables hinzufügen:**
   
   Scrolle zu **"Environment Variables"** und klicke **"Add Environment Variable"**:
   
   | Key | Value |
   |-----|-------|
   | `ISERV_COOKIE_SAT` | `eL5LYUJZkdlZXcH...` (dein kompletter Cookie-Wert) |
   | `ISERV_COOKIE_SATID` | `6651d454-9427...` (dein kompletter Cookie-Wert) |
   | `ISERV_COOKIE_SESSION` | `XagLHANcf5cj7c6...` (dein kompletter Cookie-Wert) |
   | `PORT` | `10000` (Render's default) |

5. **Deploy!**
   - Klicke **"Create Web Service"**
   - Warte 2-5 Minuten
   - Du bekommst eine URL: `https://vertretungsplan-backend.onrender.com`

### Option B: Ohne GitHub (Manuell)

1. **In Render Dashboard:**
   - **"New +"** → **"Web Service"**
   - Wähle **"Deploy from Git"** ODER **"Deploy an existing image"**
   
2. **Bei "Public Git Repository":**
   - Du kannst auch einen GitLab/Bitbucket Link nutzen

3. **Folge den gleichen Settings wie oben** (Name, Commands, Environment Variables)

---

## 🌐 Schritt 4: Frontend deployen (Netlify)

1. **Gehe zu https://netlify.com**
2. **Sign up** (kostenlos)
3. **Drag & Drop:**
   - Ziehe `vertretungsplan-app.html` in den Netlify Upload-Bereich
   
4. **WICHTIG: Frontend anpassen:**
   
   Öffne `vertretungsplan-app.html` und ändere die Backend-URL:
   
   ```javascript
   // Alt:
   fetch('http://localhost:5000/api/check', {
   
   // Neu:
   fetch('https://vertretungsplan-backend.onrender.com/api/check', {
   ```
   
   Ersetze `vertretungsplan-backend.onrender.com` mit deiner echten Render-URL!

5. **Re-upload:**
   - Lade die geänderte `vertretungsplan-app.html` nochmal hoch
   - Netlify gibt dir eine URL: `https://vertretungsplan-xyz.netlify.app`

---

## ✅ Schritt 5: Testen

1. **Backend testen:**
   ```
   https://vertretungsplan-backend.onrender.com/api/health
   ```
   Sollte zeigen:
   ```json
   {
     "status": "ok",
     "cookies_loaded": true,
     "cookies_count": 3
   }
   ```

2. **Frontend öffnen:**
   ```
   https://vertretungsplan-xyz.netlify.app
   ```
   
3. **Teste mit deiner Klasse!**

---

## 🔄 Cookies erneuern

Cookies laufen nach einiger Zeit ab!

**Wenn die App sagt "Session abgelaufen":**

1. Gehe zu Render Dashboard
2. Wähle dein Web Service
3. **Environment** → Edit Variables
4. Hole neue Cookies aus Chrome (F12 → Application → Cookies)
5. Ersetze die alten Cookie-Werte mit den neuen
6. Klicke **"Save Changes"**
7. Render startet automatisch neu

---

## 💡 Tipps

### Performance:
- Render's Free Plan schläft nach 15 Minuten Inaktivität
- Erster Request nach dem Schlafen dauert ~30 Sekunden (Cold Start)
- Für 24/7 Uptime: Upgrade zu Starter Plan ($7/Monat)

### Sicherheit:
- ✅ Cookies sind in Environment Variables sicher
- ✅ Niemand kann sie sehen (außer dir im Dashboard)
- ✅ Nicht in Code oder GitHub

### Custom Domain:
- Auf Render: Settings → Custom Domains
- Auf Netlify: Domain Settings → Add custom domain
- Z.B. `vertretungsplan.deine-domain.de`

### Automatische Updates:
- Bei GitHub-Verbindung: Jeder Git Push deployed automatisch neu
- Ohne GitHub: Manuell in Render Dashboard → "Manual Deploy"

---

## 🐛 Troubleshooting

**"Application failed to respond"**
- Logs checken: Dashboard → Logs
- Sind alle Environment Variables gesetzt?
- Python Dependencies installiert?

**"Cookies nicht geladen"**
- Environment Variables prüfen
- Keine Leerzeichen in Cookie-Werten
- Komplette Werte kopiert?

**"PDF konnte nicht heruntergeladen werden"**
- Cookies abgelaufen → Neue holen
- IServ down?

---

## 📊 Kosten

**Render Free Plan:**
- ✅ 750 Stunden/Monat kostenlos
- ✅ Automatischer Sleep nach 15min Inaktivität
- ✅ Perfekt für kleine Projekte

**Netlify Free Plan:**
- ✅ 100 GB Bandwidth/Monat
- ✅ Unlimited Sites
- ✅ Automatisches HTTPS

**Gesamt: 0€ / Monat!** 🎉

---

Fertig! Deine App ist jetzt online und von überall erreichbar! 🚀
