import os
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from datetime import datetime

# 1. جلب المفاتيح السرية من السحابة
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

# 🎯 تنظيف الـ ID تلقائياً برمجياً من أي مسافات أو علامات تنصيص زائدة لمنع خطأ 404
FILE_ID = os.environ.get("DRIVE_FILE_ID", "").strip().replace('"', '').replace("'", "")

def main():
    print("🔄 جاري الاتصال بجوجل درايف...")
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # 2. تنزيل الداتابيز الحالية
    print(f"📥 جاري سحب الداتابيز (ID: {FILE_ID})...")
    
    # 🎯 تفعيل supportsAllDrives لحل مشكلة الحسابات المشتركة أو الجامعية
    request = service.files().get_media(fileId=FILE_ID, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    database = json.loads(fh.read().decode('utf-8'))

    # 3. اختبار التعديل (إضافة ختم زمني)
    print("✍️ جاري إضافة الختم الزمني للاختبار...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    database["metadata"]["last_cloud_sync"] = now

    # 4. إعادة رفع الملف المحدث
    print("📤 جاري رفع الداتابيز المحدثة للدرايف...")
    updated_data = json.dumps(database, ensure_ascii=False, indent=4).encode('utf-8')
    fh_upload = io.BytesIO(updated_data)
    media = MediaIoBaseUpload(fh_upload, mimetype='application/json', resumable=True)
    
    # 🎯 تفعيل supportsAllDrives أيضاً عند الرفع والتحديث
    service.files().update(fileId=FILE_ID, media_body=media, supportsAllDrives=True).execute()
    print(f"🎉 تمت العملية بنجاح! الوقت المسجل في الدرايف الآن: {now}")

if __name__ == '__main__':
    main()
