import os
import json
import io
import requests
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

# =========================================================================
# 🪓 [مكانك المخصص] هنا بتلصق دوال الشفط والتحليل اللي كتبتها بالماضي
# =========================================================================
def scrape_new_player_data(player_url):
    try:
        response = requests.get(player_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        return {"url": player_url, "name": "لاعب جديد تم رصده", "updated_at": str(datetime.now())}
    except:
        return None

def scrape_new_match_data(match_url):
    try:
        response = requests.get(match_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        return {"url": match_url, "title": "مباراة جديدة تم رصدها", "events": []}
    except:
        return None
# =========================================================================

def get_drive_service():
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

# 🎯 الدالة السحرية: بتبحث عن الملف بالاسم وبتسحب الآي دي تبعه لحالها
def get_file_id_dynamically(service, filename="wikipedia_database.json"):
    print(f"🔍 جاري البحث عن ملف '{filename}' تلقائياً في حساب الروبوت...")
    query = f"name='{filename}' and trashed=false"
    results = service.files().list(
        q=query,
        pageSize=1,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    items = results.get('files', [])
    
    if not items:
        raise Exception(f"❌ الروبوت لم يجد ملفاً باسم '{filename}'. تأكد من وجوده داخل المجلد المشارك.")
    
    found_id = items[0]['id']
    print(f"✅ تم العثور على الملف بنجاح! (ID: {found_id})")
    return found_id

def download_database(service, file_id):
    print("📥 جاري سحب الداتابيز الحالية من جوجل درايف...")
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return json.loads(fh.read().decode('utf-8'))

def upload_database(service, database, file_id):
    print("📤 جاري حفظ ورفع الداتابيز المحدثة إلى جوجل درايف...")
    updated_data = json.dumps(database, ensure_ascii=False, indent=4).encode('utf-8')
    fh_upload = io.BytesIO(updated_data)
    media = MediaIoBaseUpload(fh_upload, mimetype='application/json', resumable=True)
    service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()

def check_wikipedia_for_updates():
    print("🔍 الرادار السحابي يفحص ويكيبيديا الآن بحثاً عن جديد...")
    # هنا يتم وضع روابط أو كود جلب المباريات الجديدة
    return [], []

def main():
    service = get_drive_service()
    
    # 1. البحث التلقائي عن الملف (بدل استخدام الأسرار اليدوية)
    dynamic_file_id = get_file_id_dynamically(service, "wikipedia_database.json")
    
    # 2. تنزيل الملف باستخدام الآي دي المكتشف
    db = download_database(service, dynamic_file_id)
    
    new_players_urls, new_matches_urls = check_wikipedia_for_updates()
    
    if new_players_urls:
        print(f"🏃‍♂️ تم رصد {len(new_players_urls)} لاعب جديد. جاري الشفط...")
        for url in new_players_urls:
            player_data = scrape_new_player_data(url)
            if player_data:
                db["players"].append(player_data)
                
    if new_matches_urls:
        print(f"⚽ تم رصد {len(new_matches_urls)} مباراة جديدة. جاري الشفط...")
        for url in new_matches_urls:
            match_data = scrape_new_match_data(url)
            if match_data:
                db["matches"].append(match_data)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db["metadata"]["last_cloud_sync"] = now_str
    db["metadata"]["total_players"] = len(db.get("players", []))
    db["metadata"]["total_matches"] = len(db.get("matches", []))
    
    upload_database(service, db, dynamic_file_id)
    print(f"🎉 الماكينة السحابية اختتمت عملها بنجاح! الختم الزمني الحالي: {now_str}")
    print(f"📊 الإجمالي الحالي بالملف النهائي: {len(db.get('players', []))} لاعب | {len(db.get('matches', []))} مباراة.")

if __name__ == '__main__':
    main()
