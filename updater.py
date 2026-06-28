import os
import json
import io
import requests
import re
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from datetime import datetime, timedelta

# =========================================================================
# ⚙️ إعدادات التصريح السحابي (Cloud Credentials)
# =========================================================================
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

# =========================================================================
# 🪓 محرك الشفط الكروي (The Scraping Engine)
# =========================================================================
def scrape_new_player_data(player_url):
    """دالة استخراج بيانات اللاعبين الجديدة أو المحدثة"""
    try:
        response = requests.get(player_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        
        name_tag = soup.find('h1', id='firstHeading')
        if not name_tag:
            return None
            
        player_data = {
            "url": player_url,
            "name": name_tag.text.strip(),
            "club_career": [],
            "team_achievements": [],
            "individual_achievements": [],
            "updated_at": str(datetime.now())
        }

        # 1. سحب المسيرة من صندوق المعلومات (بما فيها وظيفة المساعد)
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    text = " | ".join([c.text.strip() for c in cols])
                    # فلترة سريعة لالتقاط أسطر الأندية والمسيرة
                    if any(char.isdigit() for char in text):
                        player_data["club_career"].append(re.sub(r'\[\d+\]', '', text)) # تنظيف أرقام المراجع

        # 2. سحب الإنجازات وفصل الفردي عن الجماعي
        achievements_heading = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'إنجازات' in tag.text)
        if achievements_heading:
            current_section = achievements_heading.find_next_sibling()
            is_individual = False
            
            while current_section and current_section.name not in ['h2']:
                text_content = current_section.text.strip()
                
                # رادار تحويل المسار للجوائز الفردية
                if 'فردية' in text_content or 'الفردية' in text_content:
                    is_individual = True
                    
                if current_section.name in ['ul']:
                    items = [re.sub(r'\[\d+\]', '', li.text.strip()) for li in current_section.find_all('li')]
                    if is_individual:
                        player_data["individual_achievements"].extend(items)
                    else:
                        player_data["team_achievements"].extend(items)
                
                current_section = current_section.find_next_sibling()

        return player_data
    except Exception as e:
        print(f"❌ خطأ أثناء شفط بيانات اللاعب {player_url}: {e}")
        return None

def scrape_new_match_data(match_url):
    """دالة استخراج بيانات المباريات الجديدة"""
    try:
        response = requests.get(match_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        
        title_tag = soup.find('h1', id='firstHeading')
        if not title_tag:
            return None
            
        match_data = {
            "url": match_url,
            "title": title_tag.text.strip(),
            "score": "",
            "date": "",
            "details": [],
            "updated_at": str(datetime.now())
        }
        
        # سحب صندوق معلومات المباراة الرئيسي
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                text = row.text.strip()
                if '-' in text or '–' in text:
                    match_data["score"] = text
                elif 'تاريخ' in text:
                    match_data["date"] = text.replace('تاريخ', '').strip()
                elif text:
                    match_data["details"].append(re.sub(r'\[\d+\]', '', text))
        
        return match_data
    except Exception as e:
        print(f"❌ خطأ أثناء شفط بيانات المباراة {match_url}: {e}")
        return None

# =========================================================================
# ☁️ السيرفر السحابي والاتصال بقواعد البيانات (The Cloud Infrastructure)
# =========================================================================
def get_drive_service():
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_file_id_dynamically(service, filename="wikipedia_database.json"):
    print(f"🔍 البحث عن ملف '{filename}'...")
    results = service.files().list(
        q=f"name='{filename}' and trashed=false",
        pageSize=1, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    items = results.get('files', [])
    if not items: raise Exception(f"❌ لم يتم العثور على الملف '{filename}'.")
    return items[0]['id']

def download_database(service, file_id):
    print("📥 جاري سحب الداتابيز المركزية...")
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    return json.loads(fh.read().decode('utf-8'))

def upload_database(service, database, file_id):
    print("📤 جاري رفع الداتابيز المحدثة (Federated Model)...")
    updated_data = json.dumps(database, ensure_ascii=False, indent=4).encode('utf-8')
    fh_upload = io.BytesIO(updated_data)
    media = MediaIoBaseUpload(fh_upload, mimetype='application/json', resumable=True)
    service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()

def get_recent_wikipedia_changes(category_title, hours=24):
    """استخدام API ويكيبيديا لجلب التعديلات خلال آخر 24 ساعة"""
    url = "https://ar.wikipedia.org/w/api.php"
    yesterday = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": category_title,
        "cmsort": "timestamp", "cmdir": "desc", "cmstart": yesterday,
        "cmlimit": "30", "format": "json" # تحديد سقف السحب لتخفيف الضغط
    }
    try:
        response = requests.get(url, params=params).json()
        pages = response.get('query', {}).get('categorymembers', [])
        return [f"https://ar.wikipedia.org/wiki/{page['title'].replace(' ', '_')}" for page in pages]
    except:
        return []

# =========================================================================
# 🚀 دورة التشغيل الرئيسية (Main Pipeline)
# =========================================================================
def main():
    service = get_drive_service()
    dynamic_file_id = get_file_id_dynamically(service, "wikipedia_database.json")
    db = download_database(service, dynamic_file_id)
    
    print("📡 تشغيل رادار ويكيبيديا لمسح التعديلات الأخيرة...")
    new_players_urls = get_recent_wikipedia_changes("تصنيف:لاعبو_كرة_قدم")
    new_matches_urls = get_recent_wikipedia_changes("تصنيف:مباريات_كرة_قدم")
    
    # فهارس لحل التعارضات وتحديث القديم بدل تكراره (Clash Resolution)
    existing_players = {p.get('url'): i for i, p in enumerate(db.get("players", []))}
    existing_matches = {m.get('url'): i for i, m in enumerate(db.get("matches", []))}

    if new_players_urls:
        print(f"🏃‍♂️ جاري عمل Update لـ {len(new_players_urls)} لاعب...")
        for url in new_players_urls:
            player_data = scrape_new_player_data(url)
            if player_data and player_data["name"]:
                if url in existing_players:
                    db["players"][existing_players[url]] = player_data
                else:
                    db["players"].append(player_data)

    if new_matches_urls:
        print(f"⚽ جاري عمل Update لـ {len(new_matches_urls)} مباراة...")
        for url in new_matches_urls:
            match_data = scrape_new_match_data(url)
            if match_data and match_data["title"]:
                if url in existing_matches:
                    db["matches"][existing_matches[url]] = match_data
                else:
                    db["matches"].append(match_data)

    # التحديثات النهائية والختم الزمني
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db["metadata"]["last_cloud_sync"] = now_str
    db["metadata"]["total_players"] = len(db.get("players", []))
    db["metadata"]["total_matches"] = len(db.get("matches", []))
    
    upload_database(service, db, dynamic_file_id)
    print("="*60)
    print(f"🎉 تم تحديث النظام بنجاح! الإجمالي: {db['metadata']['total_players']} لاعب | {db['metadata']['total_matches']} مباراة.")
    print("="*60)

if __name__ == '__main__':
    main()
