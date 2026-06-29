import os
import requests
from datetime import datetime

# ==========================================
# قراءة الإعدادات من سيرفر جيتهاب مباشرة (GitHub Actions)
# ==========================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# GITHUB_REPOSITORY بيسحب اسم المستودع تلقائياً (مثال: abdallahdraz/Wiki-Football-Auto)
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY") 
FILE_PATH = "wikipedia_database.json" # اسم ملف الداتابيز الكامل تبعك

def create_release_and_upload():
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        print("❌ خطأ: لم يتم العثور على توكن جيتهاب أو اسم المستودع. تأكد من إعدادات GitHub Actions.")
        return

    version_tag = "v" + datetime.now().strftime("%Y%m%d%H%M")
    print(f"🚀 جاري إنشاء إصدار جديد: {version_tag}...")

    # 1. إنشاء الإصدار (Release)
    release_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    release_data = {
        "tag_name": version_tag,
        "name": f"تحديث تلقائي للداتابيز {version_tag}",
        "body": "تم التحديث تلقائياً عبر GitHub Actions 🤖",
        "draft": False,
        "prerelease": True 
    }

    response = requests.post(release_url, headers=headers, json=release_data)
    
    if response.status_code != 201:
        print("❌ فشل إنشاء الإصدار!")
        print(response.text)
        return

    release_info = response.json()
    upload_url = release_info["upload_url"].replace("{?name,label}", f"?name=wikipedia_database.json")

    print("✅ تم إنشاء الإصدار! جاري رفع ملف الداتابيز...")

    # 2. رفع الملف كـ Asset
    upload_headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    with open(FILE_PATH, "rb") as f:
        upload_response = requests.post(upload_url, headers=upload_headers, data=f)

    if upload_response.status_code == 201:
        print("🎉 تم رفع الداتابيز المحدثة بنجاح!")
    else:
        print("❌ فشل رفع الملف:")
        print(upload_response.text)

if __name__ == "__main__":
    if not os.path.exists(FILE_PATH):
        print(f"❌ الملف {FILE_PATH} غير موجود!")
    else:
        create_release_and_upload()
