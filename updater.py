import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_JSON = os.environ.get("GCP_CREDENTIALS")

def main():
    print("🔍 جاري فحص بصر الروبوت (شو الملفات اللي قادر يشوفها؟)...")
    
    try:
        creds_dict = json.loads(CREDENTIALS_JSON)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        # الطلب من الروبوت جرد كل الملفات المسموح له برؤيتها
        results = service.files().list(
            pageSize=10, 
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        items = results.get('files', [])

        print("\n=============================================")
        if not items:
            print("❌ الروبوت أعمى تماماً! لا يوجد أي ملف قادر يوصله.")
            print("السبب إما أن المجلد يمنع التوريث، أو أن إيميلك (جامعي/شركة) يمنع المشاركة الخارجية.")
        else:
            print("✅ الروبوت يرى الملفات التالية:")
            for item in items:
                print(f"اسم الملف: {item['name']} | الآي دي: {item['id']}")
        print("=============================================\n")

    except Exception as e:
        print(f"حدث خطأ أثناء الفحص: {e}")

if __name__ == '__main__':
    main()
