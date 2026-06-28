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
FILE_ID = os.environ.get("DRIVE_FILE_ID", "").strip().replace('"', '').replace("'", "")

# =========================================================================
# 🪓 [مكانك المخصص] هنا بتلصق دوال الشفط والتحليل اللي كتبتها بالماضي
# =========================================================================
def scrape_new_player_data(player_url):
    """
    هنا بتستدعي كود قشط صفحة اللاعب (V13) اللي عملناه.
    بياخد الـ URL وبيرجع دكشينري جواه (الاسم، المسيرة، الإنجازات الفردية والجماعية).
    """
    # مثال هيكلي سريع (استبدله بكودك الفعلي):
    try:
        response = requests.get(player_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        # ... كود الشفط تبعك ...
        return {"url": player_url, "name": "لاعب جديد تم رصده", "updated_at": str(datetime.now())}
    except:
        return None

def scrape_new_match_data(match_url):
    """
    هنا بتستدعي كود قشط صفحة المباراة (V10) اللي عملناه بالماضي.
    بياخد الـ URL وبيرجع (الأهداف، التشكيلات، التبديلات، القصة الدرامية، الكروت).
    """
    try:
        response = requests.get(match_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        # ... كود الشفط تبعك ...
        return {"url": match_url, "title": "مباراة جديدة تم رصدها", "events": []}
    except:
        return None
# =========================================================================

def get_drive_service():
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def download_database(service):
    print("📥 جاري سحب الداتابيز الحالية من جوجل درايف...")
    request = service.files().get_media(fileId=FILE_ID, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return json.loads(fh.read().decode('utf-8'))

def upload_database(service, database):
    print("📤 جاري حفظ ورفع الداتابيز المحدثة إلى جوجل درايف...")
    updated_data = json.dumps(database, ensure_ascii=False, indent=4).encode('utf-8')
    fh_upload = io.BytesIO(updated_data)
    media = MediaIoBaseUpload(fh_upload, mimetype='application/json', resumable=True)
    service.files().update(fileId=FILE_ID, media_body=media, supportsAllDrives=True).execute()

def check_wikipedia_for_updates():
    """
    رادار التحديث (Delta Sync)
    هنا بنبرمج الكود يلف على تصنيفات ويكيبيديا للمباريات الجديدة أو التعديلات الأخيرة
    """
    print("🔍 الرادار السحابي يفحص ويكيبيديا الآن بحثاً عن جديد...")
    new_players_urls = [] # هنا بنجمع روابط اللعيبة الجداد لو انوجدوا اليوم
    new_matches_urls = [] # هنا بنجمع روابط المباريات الجديدة (مثل مباريات أمس)
    
    # [ملاحظة تكتيكية]: يمكنك استخدام ويكيبيديا API لفحص التعديلات الأخيرة 
    # أو ببساطة عمل سكراب لصفحة "البطولة الحالية" لتصيد مباريات الجولة الجديدة.
    
    return new_players_urls, new_matches_urls

def main():
    service = get_drive_service()
    db = download_database(service)
    
    # تفعيل الرادار لجمع الفروقات (Delta)
    new_players_urls, new_matches_urls = check_wikipedia_for_updates()
    
    has_updates = False
    
    # 1. تحديث وصيد اللاعبين الجدد
    if new_players_urls:
        print(f"🏃‍♂️ تم رصد {len(new_players_urls)} لاعب جديد. جاري الشفط...")
        for url in new_players_urls:
            player_data = scrape_new_player_data(url)
            if player_data:
                db["players"].append(player_data)
                has_updates = True
                
    # 2. تحديث وصيد المباريات الجديدة
    if new_matches_urls:
        print(f"⚽ تم رصد {len(new_matches_urls)} مباراة جديدة. جاري الشفط بالتفاصيل...")
        for url in new_matches_urls:
            match_data = scrape_new_match_data(url)
            if match_data:
                db["matches"].append(match_data)
                has_updates = True

    # 3. تحديث الـ Metadata والختم الزمني في كل الأحوال للتأكيد
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db["metadata"]["last_cloud_sync"] = now_str
    db["metadata"]["total_players"] = len(db["players"])
    db["metadata"]["total_matches"] = len(db["matches"])
    
    # رفع الملف فقط إذا انضافت داتا جديدة أو لتحديث الختم الزمني للرقابة
    upload_database(service, db)
    print(f"🎉 الماكينة السحابية اختتمت عملها بنجاح! الختم الزمني الحالي: {now_str}")
    print(f"📊 الإجمالي الحالي بالملف النهائي: {len(db['players'])} لاعب | {len(db['matches'])} مباراة.")

if __name__ == '__main__':
    main()
