from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import re
import json
import io
import os

# Try to import PDF libraries
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    print("⚠️  PyPDF2 nicht installiert")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("⚠️  pdfplumber nicht installiert")

app = Flask(__name__)
CORS(app)

# Direct PDF URL structure
PDF_BASE_URL = "https://kranichgym.de/iserv/plan/show/raw/1%20Vertretungspl%C3%A4ne"

def load_cookies():
    """Load cookies from environment variables or cookies.json file"""
    
    # Try environment variables first (for deployment)
    cookie_sat = os.getenv('ISERV_COOKIE_SAT')
    cookie_satid = os.getenv('ISERV_COOKIE_SATID')
    cookie_session = os.getenv('ISERV_COOKIE_SESSION')
    
    if cookie_sat or cookie_satid or cookie_session:
        cookies = {}
        if cookie_sat:
            cookies['IServSAT'] = cookie_sat
        if cookie_satid:
            cookies['IServSATId'] = cookie_satid
        if cookie_session:
            cookies['IServSession'] = cookie_session
        
        print(f"✓ Cookies aus Umgebungsvariablen geladen: {len(cookies)}")
        return cookies
    
    # Fallback: Try cookies.json file (for local development)
    try:
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
            if cookies:
                print(f"✓ Cookies aus cookies.json geladen: {len(cookies)}")
            return cookies
    except FileNotFoundError:
        print("⚠️  Keine Cookies gefunden!")
        print("Setze Umgebungsvariablen: ISERV_COOKIE_SAT, ISERV_COOKIE_SATID, ISERV_COOKIE_SESSION")
        print("Oder erstelle cookies.json für lokale Entwicklung")
        return {}

def build_pdf_url(date_offset=0):
    """Build the direct PDF URL for a specific date"""
    target_date = datetime.now() + timedelta(days=date_offset)
    date_str = target_date.strftime("%d.%m.%y")
    pdf_url = f"{PDF_BASE_URL}/{date_str}.pdf"
    return pdf_url

def download_pdf(session, pdf_url):
    """Download PDF from URL"""
    try:
        print(f"Downloading PDF: {pdf_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf',
            'Referer': 'https://kranichgym.de/iserv/',
        }
        
        response = session.get(pdf_url, headers=headers, timeout=15)
        
        print(f"Response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            if 'application/pdf' in response.headers.get('Content-Type', ''):
                print(f"✓ PDF downloaded ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"⚠️  Response ist kein PDF: {response.headers.get('Content-Type')}")
                return None
        elif response.status_code == 404:
            print(f"✗ PDF nicht gefunden (404)")
            return None
        else:
            print(f"✗ Fehler: Status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Fehler beim Download: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_text_from_pdf(pdf_content):
    """Extract text from PDF using available libraries"""
    
    if not pdf_content:
        return None
    
    # Try pdfplumber first (better for tables)
    if HAS_PDFPLUMBER:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                print(f"✓ pdfplumber: {len(text)} Zeichen extrahiert")
                return text
        except Exception as e:
            print(f"pdfplumber Fehler: {e}")
    
    # Try PyPDF2
    if HAS_PYPDF2:
        try:
            import PyPDF2
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            print(f"✓ PyPDF2: {len(text)} Zeichen extrahiert")
            return text
        except Exception as e:
            print(f"PyPDF2 Fehler: {e}")
    
    print("⚠️  Keine PDF-Library verfügbar!")
    return None

def parse_vertretungsplan_text(text, class_name, teacher_name=None):
    """Parse the extracted PDF text for a specific class and/or teacher"""
    if not text:
        return []
    
    entries = []
    lines = text.split('\n')
    
    print(f"\n{'='*60}")
    print(f"Suche nach Klasse: {class_name.upper()}")
    if teacher_name:
        print(f"Suche nach Lehrer: {teacher_name}")
    print(f"{'='*60}")
    
    class_upper = class_name.upper().strip()
    
    match = re.match(r'^(\d+|Q\d+)([A-Z])?$', class_upper)
    if match:
        grade = match.group(1)
        letter = match.group(2) if match.group(2) else ""
    else:
        grade = class_upper
        letter = ""
    
    print(f"Parsed class: Grade={grade}, Letter={letter if letter else 'none'}")
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if not line or len(line) < 5:
            continue
        
        line_upper = line.upper()
        
        class_matched = False
        match_reason = ""
        
        # Method 1: Exact match
        if class_upper in line_upper:
            class_matched = True
            match_reason = "exact"
        
        # Method 2: Dot notation (e.g., "11A.." means multiple classes)
        if not class_matched and letter:
            dot_pattern = rf'\b{re.escape(grade)}[A-Z]+\.\.+\b'
            if re.search(dot_pattern, line_upper):
                class_matched = True
                match_obj = re.search(dot_pattern, line_upper)
                match_reason = f"dot notation: {match_obj.group()}"
                print(f"   Dot notation gefunden: {match_obj.group()} → betrifft {class_upper}")
        
        # Method 3: Multi-class patterns (e.g., "11ABCD")
        if not class_matched and letter:
            multi_class_pattern = rf'\b{re.escape(grade)}[A-Z]{{2,}}\b'
            matches = re.findall(multi_class_pattern, line_upper)
            
            for match_text in matches:
                letters_part = match_text[len(grade):]
                
                if letter in letters_part:
                    class_matched = True
                    match_reason = f"multi-class: {match_text} enthält {letter}"
                    print(f"   Multi-class: {match_text} enthält {grade}{letter}")
                    break
        
        # Teacher matching
        teacher_matched = False
        if teacher_name:
            teacher_upper = teacher_name.upper()
            if teacher_upper in line_upper:
                teacher_matched = True
                match_reason += " + teacher match" if match_reason else "teacher"
        
        # Decide if we should include this line
        should_include = False
        
        if teacher_name:
            if class_matched and teacher_matched:
                should_include = True
            elif teacher_matched:
                should_include = True
                if not class_matched:
                    match_reason += " (anderer Kurs)"
        else:
            should_include = class_matched
        
        if not should_include:
            continue
        
        print(f"\n✓ Match ({match_reason}) Zeile {i}: {line[:80]}...")
        
        parts = line.split()
        
        if len(parts) < 2:
            continue
        
        entry = {
            'id': len(entries) + 1,
            'class': class_name.upper(),
            'raw': line
        }
        
        # Find mentioned classes
        mentioned_classes = re.findall(r'\b\d+[A-Z]+\.{0,2}\b|\bQ\d+[A-Z]*\.{0,2}\b', line_upper)
        if mentioned_classes:
            entry['mentioned_classes'] = ', '.join(mentioned_classes)
        
        # Extract lesson number
        if parts and re.match(r'^\d+(-\d+)?$', parts[0]):
            entry['lesson'] = parts[0]
        
        # Detect status
        if 'ENTFÄLLT' in line_upper or 'ENTFALL' in line_upper:
            entry['status'] = 'cancelled'
            entry['note'] = 'Unterricht entfällt'
        elif 'FÄLLT AUS' in line_upper:
            entry['status'] = 'cancelled'
            entry['note'] = 'Fällt aus'
        elif 'EVA' in line_upper:
            entry['status'] = 'cancelled'
            entry['note'] = 'EVA (Eigenverantwortliches Arbeiten)'
        elif 'VERTR' in line_upper or 'VERTRETUNG' in line_upper:
            entry['status'] = 'substitute'
            entry['note'] = 'Vertretung'
        elif 'VERLEGT' in line_upper or 'VERLEGUNG' in line_upper:
            entry['status'] = 'substitute'
            entry['note'] = 'Stunde verlegt'
        else:
            entry['status'] = 'normal'
        
        # Extract subject
        subjects = {
            'MA': 'Mathematik', 'DE': 'Deutsch', 'EN': 'Englisch',
            'FR': 'Französisch', 'SP': 'Spanisch', 'LA': 'Latein',
            'PH': 'Physik', 'CH': 'Chemie', 'BI': 'Biologie',
            'GE': 'Geschichte', 'EK': 'Erdkunde', 'PO': 'Politik',
            'RE': 'Religion', 'ET': 'Ethik', 'IF': 'Informatik',
            'WI': 'Wirtschaft', 'MU': 'Musik', 'KU': 'Kunst',
            'SPO': 'Sport', 'RU': 'Religion'
        }
        
        for part in parts:
            part_upper = part.upper().strip('.,;:')
            if part_upper in subjects:
                entry['subject'] = subjects[part_upper]
                break
        
        # Extract room
        for part in parts:
            if re.match(r'^\d{2}\.\d{2}\.\d{2}$', part):
                entry['room'] = part
                break
        
        # Extract teacher
        for idx, part in enumerate(parts):
            if part in ['Hr.', 'Fr.', 'Herr', 'Frau'] and idx + 1 < len(parts):
                entry['teacher'] = f"{part} {parts[idx + 1]}"
                break
        
        if 'teacher' not in entry:
            for part in parts:
                if len(part) > 2 and part[0].isupper() and not part.isupper():
                    if not any(subj in part.upper() for subj in subjects.keys()):
                        entry['teacher'] = part
                        break
        
        entries.append(entry)
        print(f"   → Stunde: {entry.get('lesson', '?')}, "
              f"Fach: {entry.get('subject', '?')}, "
              f"Status: {entry.get('status', '?')}, "
              f"Klassen: {entry.get('mentioned_classes', class_upper)}, "
              f"Lehrer: {entry.get('teacher', '?')}")
    
    print(f"\n{'='*60}")
    print(f"✓ {len(entries)} Einträge gefunden")
    print(f"{'='*60}\n")
    
    return entries

def get_plan(date_offset=0):
    """Main function to fetch and parse the substitution plan"""
    cookies = load_cookies()
    
    if not cookies:
        return None, "Keine Cookies gefunden - bitte Umgebungsvariablen setzen"
    
    session = requests.Session()
    
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='kranichgym.de')
    
    try:
        pdf_url = build_pdf_url(date_offset)
        
        print(f"\n{'='*60}")
        print(f"Abrufen: {pdf_url}")
        print(f"{'='*60}")
        
        pdf_content = download_pdf(session, pdf_url)
        
        if not pdf_content:
            return None, "PDF konnte nicht heruntergeladen werden"
        
        text = extract_text_from_pdf(pdf_content)
        
        if not text:
            return None, "Konnte Text nicht aus PDF extrahieren"
        
        return text, None
            
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        return None, str(e)

@app.route('/api/check', methods=['POST'])
def check_plan():
    """API endpoint to check substitution plan"""
    try:
        data = request.json
        class_name = data.get('className', '').strip()
        teacher_name = data.get('teacherName', '').strip()
        date_type = data.get('dateType', 'today')
        
        if not class_name:
            return jsonify({'error': 'Klasse fehlt'}), 400
        
        date_offset_map = {
            'today': 0,
            'tomorrow': 1
        }
        date_offset = date_offset_map.get(date_type, 0)
        
        print(f"\n{'='*60}")
        print(f"ANFRAGE: Klasse {class_name}", end="")
        if teacher_name:
            print(f", Lehrer {teacher_name}", end="")
        print(f", {date_type}")
        print(f"{'='*60}")
        
        text, error = get_plan(date_offset)
        
        if error:
            return jsonify({'error': error}), 500
        
        entries = parse_vertretungsplan_text(text, class_name, teacher_name if teacher_name else None)
        
        response_data = {
            'hasChanges': len(entries) > 0,
            'entries': entries,
            'className': class_name.upper(),
            'teacherName': teacher_name if teacher_name else None,
            'date': (datetime.now() + timedelta(days=date_offset)).strftime("%d.%m.%Y")
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server-Fehler: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    cookies = load_cookies()
    return jsonify({
        'status': 'ok',
        'cookies_loaded': len(cookies) > 0,
        'cookies_count': len(cookies),
        'has_pypdf2': HAS_PYPDF2,
        'has_pdfplumber': HAS_PDFPLUMBER,
        'pdf_support': HAS_PYPDF2 or HAS_PDFPLUMBER
    })

@app.route('/')
def index():
    """Root"""
    return jsonify({
        'message': 'Vertretungsplan API v5 (Production Ready)',
        'status': 'running'
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Vertretungsplan Backend v5 (Production)")
    print("="*60)
    
    cookies = load_cookies()
    if not cookies:
        print("\n❌ KEINE COOKIES!")
        print("\nFür Deployment:")
        print("  Setze Umgebungsvariablen:")
        print("  - ISERV_COOKIE_SAT")
        print("  - ISERV_COOKIE_SATID")
        print("  - ISERV_COOKIE_SESSION")
        print("\nFür lokal:")
        print("  Erstelle cookies.json")
    else:
        print(f"\n✓ Cookies geladen: {len(cookies)}")
    
    if not HAS_PYPDF2 and not HAS_PDFPLUMBER:
        print("\n⚠️  Keine PDF-Library!")
    else:
        print(f"\n✓ PDF-Support:")
        if HAS_PDFPLUMBER:
            print("  ✓ pdfplumber")
        if HAS_PYPDF2:
            print("  ✓ PyPDF2")
    
    print("\n" + "="*60)
    port = int(os.getenv('PORT', 5000))
    print(f"Backend läuft auf Port: {port}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
