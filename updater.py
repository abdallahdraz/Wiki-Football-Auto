import os
import json
import requests
import re
import base64
import math
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================================
# ⚙️ إعدادات مستودع جيتهاب (تأكد من الاسم)
# ==========================================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = "abdallahdraz/Wiki-Football-Auto"  # 👈 تم تعديل اسم المستودع بناءً على صورتك
NUM_PARTS = 6  # 👈 6 أجزاء لتجنب مشكلة الحجم تماماً

# 1. سحب الملف كنص خام (Raw Text)
def get_github_file_raw(filename):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        return base64.b64decode(data['content']).decode('utf-8'), data['sha']
    return "", None

# 2. رفع الملف كنص خام
def update_github_file_raw(filename, text_chunk, sha):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_encoded = base64.b64encode(text_chunk.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": f"🤖 التحديث التلقائي اليومي للجزء {filename}",
        "content": content_encoded,
        "sha": sha
    }
    
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code not in [200, 201]:
        print(f"❌ فشل رفع {filename}: {res.text}")

# 3. دوال الشفط (Scraping)
def scrape_new_player_data(player_url):
    try:
        response = requests.get(player_url, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        name_tag = soup.find('h1', id='firstHeading')
        if not name_tag: return None
            
        player_data = {
            "url": player_url,
            "target": name_tag.text.strip(),
            "career": [],
            "updated_at": str(datetime.now())
        }
        
        infobox = soup.find('table', {'class': 'infobox'})
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    text = " | ".join([c.text.strip() for c in cols])
                    if any(char.isdigit() for char in text):
                        player_data["career"].append(re.sub(r'\[\d+\]', '', text))
                        
        if player_data["career"]:
             player_data["career"] = " ⬅️ ".join(player_data["career"])
        return player_data
    except Exception as e:
        print(f"❌ خطأ بشفط {player_url}: {e}")
        return None

def get_recent_wikipedia_changes(category_title, hours=24):
    url = "https://ar.wikipedia.org/w/api.php"
    yesterday = (datetime.utcnow() - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": category_title,
        "cmsort": "timestamp", "cmdir": "desc", "cmstart": yesterday, "cmlimit": "30", "format": "json"
    }
    try:
        response = requests.get(url, params=params).json()
        return [f"https://ar.wikipedia.org/wiki/{p['title'].replace(' ', '_')}" for p in response.get('query', {}).get('categorymembers', [])]
    except: return []

# ==========================================
# 🚀 المعالجة المركزية
# ==========================================
def main():
    if not GITHUB_TOKEN:
        print("❌ لم يتم العثور على GITHUB_TOKEN.")
        return

    print("📥 جاري سحب وتجميع الأجزاء الـ 6 ككتلة نصية...")
    full_json_string = ""
    file_shas = {}

    for i in range(1, NUM_PARTS + 1):
        filename = f"wiki_part{i}.json"
        text_data, sha = get_github_file_raw(filename)
        if text_data:
            # تنظيف أي أقواس مصفوفات زائدة من الأطراف لدمجها كنص واحد صح
            text_data = text_data.strip()
            if text_data.startswith('['): text_data = text_data[1:]
            if text_data.endswith(']'): text_data = text_data[:-1]
            if full_json_string and text_data: full_json_string += ","
            full_json_string += text_data
        file_shas[filename] = sha

    # إعادة تغليف النص كمصفوفة JSON صحيحة
    full_json_string = f"[{full_json_string}]"
    
    print("🧠 جاري تحويل النص المدمج إلى داتابيز بالذاكرة...")
    try:
        db = json.loads(full_json_string)
    except Exception as e:
        print(f"❌ فشل في دمج JSON: {e}")
        return

    print("📡 رادار ويكيبيديا يبحث عن لاعبين جدد أو تعديلات...")
    new_players_urls = get_recent_wikipedia_changes("تصنيف:لاعبو_كرة_قدم")
    existing_players = {p.get('url'): idx for idx, p in enumerate(db)}

    if new_players_urls:
        print(f"🏃‍♂️ معالجة {len(new_players_urls)} تحديث...")
        for url in new_players_urls:
            player_data = scrape_new_player_data(url)
            if player_data and player_data["target"]:
                if url in existing_players:
                    db[existing_players[url]] = player_data
                else:
                    db.append(player_data)

    print("📤 جاري تقسيم المصفوفة لـ 6 أجزاء ورفعها...")
    updated_json_string = json.dumps(db, ensure_ascii=False)
    
    # التقسيم بالمسطرة
    total_chars = len(updated_json_string)
    chunk_size = math.ceil(total_chars / NUM_PARTS)
    
    for i in range(NUM_PARTS):
        chunk = updated_json_string[i * chunk_size : (i + 1) * chunk_size]
        filename = f"wiki_part{i+1}.json"
        update_github_file_raw(filename, chunk, file_shas.get(filename))
        print(f"✅ تم رفع {filename}")

if __name__ == '__main__':
    main()
