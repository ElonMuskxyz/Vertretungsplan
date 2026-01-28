from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import re
import json
import io

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
    """Load cookies from cookies.json"""
    try:
        with open('cookies.json', 'r') as f:
            cookies = json.load(f)
            if cookies:
                print(f"✓ {len(cookies)} Cookies geladen")
            return cookies
    except FileNotFoundError:
        print("⚠️  cookies.json nicht gefunden!")
        return {}

def build_pdf_url(date_offset=0):
    """Build the direct PDF URL for a specific date"""
    target_date = datetime.now() + timedelta(days=date_offset)
    
    # Format: DD.MM.YY (without leading zeros? let's try both)
    date_str = target_date.strftime("%d.%m.%y")  # e.g., 28.01.26
    
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
            # Check if it's actually a PDF
            if 'application/pdf' in response.headers.get('Content-Type', ''):
                print(f"✓ PDF downloaded ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"⚠️  Response ist kein PDF: {response.headers.get('Content-Type')}")
                # Save for debugging
                with open('response_debug.html', 'wb') as f:
                    f.write(response.content)
                return None
        elif response.status_code == 404:
            print(f"✗ PDF nicht gefunden (404) - vielleicht noch nicht veröffentlicht?")
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
    print("Installiere: python -m pip install pypdf2")
    print("Oder: python -m pip install pdfplumber")
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
    
    # Extract class components for better matching
    # e.g., "11D" -> grade="11", letter="D"
    class_upper = class_name.upper().strip()
    
    # Try to parse class format (e.g., "11D", "8C", "Q1")
    match = re.match(r'^(\d+|Q\d+)([A-Z])?$', class_upper)
    if match:
        grade = match.group(1)  # e.g., "11" or "Q1"
        letter = match.group(2) if match.group(2) else ""  # e.g., "D"
    else:
        grade = class_upper
        letter = ""
    
    print(f"Parsed class: Grade={grade}, Letter={letter if letter else 'none'}")
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines
        if not line or len(line) < 5:
            continue
        
        line_upper = line.upper()
        
        # Check class matching
        class_matched = False
        match_reason = ""
        
        # Method 1: Exact match (e.g., "11D" appears in line)
        if class_upper in line_upper:
            class_matched = True
            match_reason = "exact"
        
        # Method 2: Dot notation (e.g., "11A.." means multiple classes from that grade)
        # This typically means: 11A, 11B, 11C, 11D all affected
        if not class_matched and letter:
            # Look for patterns like "11A..", "8B..", "Q1C.."
            dot_pattern = rf'\b{re.escape(grade)}[A-Z]+\.\.+\b'
            if re.search(dot_pattern, line_upper):
                class_matched = True
                match_obj = re.search(dot_pattern, line_upper)
                match_reason = f"dot notation: {match_obj.group()}"
                print(f"   Dot notation gefunden: {match_obj.group()} → betrifft {class_upper}")
        
        # Method 3: Multi-class patterns (e.g., "11ABCD")
        if not class_matched and letter:
            # Find all potential class groups in the line
            multi_class_pattern = rf'\b{re.escape(grade)}[A-Z]{{2,}}\b'
            matches = re.findall(multi_class_pattern, line_upper)
            
            for match_text in matches:
                # Extract the letters part (everything after the grade)
                letters_part = match_text[len(grade):]
                
                # Check if our letter is in there
                if letter in letters_part:
                    class_matched = True
                    match_reason = f"multi-class: {match_text} enthält {letter}"
                    print(f"   Multi-class: {match_text} enthält {grade}{letter}")
                    break
        
        # Check teacher matching (if provided)
        teacher_matched = False
        if teacher_name:
            teacher_upper = teacher_name.upper()
            # Look for teacher name anywhere in the line
            if teacher_upper in line_upper:
                teacher_matched = True
                match_reason += " + teacher match" if match_reason else "teacher"
        
        # Decide if we should include this line
        should_include = False
        
        if teacher_name:
            # If teacher is specified, need BOTH class and teacher OR just teacher
            if class_matched and teacher_matched:
                should_include = True
            elif teacher_matched:
                # Teacher match alone is also useful
                should_include = True
                if not class_matched:
                    match_reason += " (anderer Kurs)"
        else:
            # No teacher specified, just need class match
            should_include = class_matched
        
        if not should_include:
            continue
        
        print(f"\n✓ Match ({match_reason}) Zeile {i}: {line[:80]}...")
        
        # Parse the line
        parts = line.split()
        
        if len(parts) < 2:
            continue
        
        entry = {
            'id': len(entries) + 1,
            'class': class_name.upper(),
            'raw': line
        }
        
        # Find which exact class(es) are mentioned
        mentioned_classes = re.findall(r'\b\d+[A-Z]+\b|\bQ\d+[A-Z]*\b', line_upper)
        if mentioned_classes:
            entry['mentioned_classes'] = ', '.join(mentioned_classes)
        
        # Extract lesson number (first column: 1-2, 3, 5-6, etc.)
        if parts and re.match(r'^\d+(-\d+)?$', parts[0]):
            entry['lesson'] = parts[0]
        
        # Detect status from keywords
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
        
        # Extract subject (common abbreviations)
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
        
        # Extract room number (format: 01.01.20 or similar)
        for part in parts:
            if re.match(r'^\d{2}\.\d{2}\.\d{2}$', part):
                entry['room'] = part
                break
        
        # Look for teacher names (Hr., Fr., Herr, Frau)
        # Also look for just last names (capitalized words)
        for idx, part in enumerate(parts):
            if part in ['Hr.', 'Fr.', 'Herr', 'Frau'] and idx + 1 < len(parts):
                entry['teacher'] = f"{part} {parts[idx + 1]}"
                break
        
        # If no teacher found with prefix, look for capitalized words (likely surnames)
        if 'teacher' not in entry:
            for part in parts:
                # Skip known abbreviations and class names
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
        return None, "Keine Cookies in cookies.json gefunden"
    
    session = requests.Session()
    
    # Set cookies
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='kranichgym.de')
    
    try:
        # Build PDF URL directly
        pdf_url = build_pdf_url(date_offset)
        
        print(f"\n{'='*60}")
        print(f"Abrufen: {pdf_url}")
        print(f"{'='*60}")
        
        # Download PDF
        pdf_content = download_pdf(session, pdf_url)
        
        if not pdf_content:
            return None, "PDF konnte nicht heruntergeladen werden"
        
        # Save PDF for debugging
        with open('vertretungsplan.pdf', 'wb') as f:
            f.write(pdf_content)
        print("✓ PDF gespeichert: vertretungsplan.pdf")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_content)
        
        if not text:
            return None, "Konnte Text nicht aus PDF extrahieren. Bitte installiere: python -m pip install pypdf2"
        
        # Save text for debugging
        with open('vertretungsplan.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print("✓ Text gespeichert: vertretungsplan.txt")
        
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
            'tomorrow': 1,
            'dayAfter': 2
        }
        date_offset = date_offset_map.get(date_type, 0)
        
        print(f"\n{'='*60}")
        print(f"ANFRAGE: Klasse {class_name}", end="")
        if teacher_name:
            print(f", Lehrer {teacher_name}", end="")
        print(f", {date_type}")
        print(f"{'='*60}")
        
        # Get plan
        text, error = get_plan(date_offset)
        
        if error:
            return jsonify({'error': error}), 500
        
        # Parse for class (and teacher if provided)
        entries = parse_vertretungsplan_text(text, class_name, teacher_name if teacher_name else None)
        
        # Response
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
        'message': 'Vertretungsplan API v4 (Final)',
        'pdf_url_format': f'{PDF_BASE_URL}/DD.MM.YY.pdf',
        'pdf_libraries': {
            'pypdf2': HAS_PYPDF2,
            'pdfplumber': HAS_PDFPLUMBER
        }
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Vertretungsplan Backend v4 (FINAL)")
    print("="*60)
    
    # Check cookies
    cookies = load_cookies()
    if not cookies:
        print("\n❌ FEHLT: cookies.json")
        print("Erstelle eine cookies.json mit deinen IServ-Cookies!")
    else:
        print(f"\n✓ Cookies geladen: {len(cookies)}")
    
    # Check PDF support
    if not HAS_PYPDF2 and not HAS_PDFPLUMBER:
        print("\n⚠️  WARNUNG: Keine PDF-Library!")
        print("Installiere mit:")
        print("  python -m pip install pypdf2")
        print("  ODER: python -m pip install pdfplumber")
    else:
        print(f"\n✓ PDF-Support:")
        if HAS_PDFPLUMBER:
            print("  ✓ pdfplumber")
        if HAS_PYPDF2:
            print("  ✓ PyPDF2")
    
    print("\n" + "="*60)
    print("Backend läuft auf: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
