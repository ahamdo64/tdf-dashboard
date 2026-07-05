#!/usr/bin/env python3
"""
سكربت جلب بيانات تور دو فرانس 2026 - النسخة الحقيقية فقط
يجلب البيانات من مصادر موثوقة ويحفظها في results.json

الاستخدام:
    python fetch_tdf.py              # جلب تلقائي
    python fetch_tdf.py --stage 5    # جلب مرحلة محددة
    python fetch_tdf.py --force      # إجبار الجلب حتى لو فشل سابقاً

المتطلبات:
    pip install requests beautifulsoup4
"""

import json
import sys
import os
import socket
from datetime import datetime
from typing import Dict, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False


# ============ إعدادات ============
OUTPUT_FILE = "results.json"
TDF_OFFICIAL_URL = "https://www.letour.fr/en/results"
PROCYCLINGSTATS_URL = "https://www.procyclingstats.com/race/tour-de-france/2026"
RACE_START_DATE = datetime(2026, 7, 4)  # تاريخ بداية السباق

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.letour.fr/"
}


def check_internet_connection() -> bool:
    """التحقق من وجود اتصال بالإنترنت."""
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False


def check_race_started() -> bool:
    """التحقق من أن السباق قد بدأ."""
    now = datetime.now()
    return now >= RACE_START_DATE


def fetch_from_letour(stage_number: Optional[int] = None) -> Optional[Dict]:
    """
    محاولة جلب البيانات من الموقع الرسمي لتور دو فرانس.
    """
    if not HAS_LIBS:
        print("❌ خطأ: المكتبات المطلوبة غير مثبتة")
        print("   يرجى تشغيل: pip install requests beautifulsoup4")
        return None
    
    try:
        print(f"🌐 محاولة الاتصال بـ: {TDF_OFFICIAL_URL}")
        response = requests.get(TDF_OFFICIAL_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن جدول النتائج
        results_table = soup.find('table', class_=lambda x: x and 'result' in x.lower())
        
        if not results_table:
            print("⚠️  لم يتم العثور على جدول النتائج في الصفحة")
            return None
        
        # استخراج البيانات
        results = []
        rows = results_table.find_all('tr')[1:]  # تخطي رأس الجدول
        
        for i, row in enumerate(rows, 1):
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 5:
                results.append({
                    "rank": i,
                    "rider": cols[1].get_text(strip=True),
                    "team": cols[2].get_text(strip=True),
                    "country": cols[3].get_text(strip=True) if len(cols) > 3 else "",
                    "time": cols[4].get_text(strip=True),
                    "gap": cols[5].get_text(strip=True) if len(cols) > 5 else "+0:00"
                })
        
        if not results:
            print("⚠️  جدول النتائج فارغ")
            return None
        
        # معلومات المرحلة
        stage_info = extract_stage_info(soup, stage_number)
        
        return {
            "metadata": {
                "race": "Tour de France 2026",
                "edition": 113,
                "last_updated": datetime.now().isoformat(),
                "source": "letour.fr",
                "version": "2.0"
            },
            "stage": stage_info,
            "results": results,
            "statistics": calculate_statistics(results),
            "jerseys": extract_jerseys(soup)
        }
        
    except requests.exceptions.Timeout:
        print("⏱️  انتهت مهلة الاتصال بالموقع")
        return None
    except requests.exceptions.ConnectionError:
        print("🔌 فشل الاتصال بالموقع")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ خطأ HTTP: {e}")
        return None
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return None


def fetch_from_procyclingstats(stage_number: Optional[int] = None) -> Optional[Dict]:
    """
    محاولة بديلة: جلب البيانات من ProCyclingStats.
    """
    if not HAS_LIBS:
        return None
    
    try:
        url = PROCYCLINGSTATS_URL
        if stage_number:
            url += f"/stage-{stage_number}"
        
        print(f"🌐 محاولة الاتصال بـ: {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن جدول النتائج
        results = []
        table = soup.find('table', class_='basic')
        
        if table:
            rows = table.find_all('tr')[1:]
            for i, row in enumerate(rows, 1):
                cols = row.find_all('td')
                if len(cols) >= 4:
                    results.append({
                        "rank": i,
                        "rider": cols[0].get_text(strip=True),
                        "team": cols[1].get_text(strip=True),
                        "country": cols[2].get_text(strip=True),
                        "time": cols[3].get_text(strip=True),
                        "gap": cols[4].get_text(strip=True) if len(cols) > 4 else "+0:00"
                    })
        
        if not results:
            return None
        
        return {
            "metadata": {
                "race": "Tour de France 2026",
                "edition": 113,
                "last_updated": datetime.now().isoformat(),
                "source": "procyclingstats.com",
                "version": "2.0"
            },
            "stage": {
                "number": stage_number or 1,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "completed"
            },
            "results": results,
            "statistics": calculate_statistics(results),
            "jerseys": {}
        }
        
    except Exception as e:
        print(f"⚠️  فشل الاتصال بـ ProCyclingStats: {e}")
        return None


def extract_stage_info(soup: BeautifulSoup, stage_number: Optional[int] = None) -> Dict:
    """استخراج معلومات المرحلة من الصفحة."""
    # محاولة استخراج معلومات المرحلة من الصفحة
    stage_info = {
        "number": stage_number or 1,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "start": "غير محدد",
        "end": "غير محدد",
        "distance_km": 0,
        "type": "unknown",
        "status": "completed",
        "weather": "غير متوفر"
    }
    
    # محاولة استخراج المسافة
    distance_elem = soup.find(string=lambda s: s and 'km' in s.lower())
    if distance_elem:
        import re
        match = re.search(r'(\d+\.?\d*)\s*km', distance_elem)
        if match:
            stage_info["distance_km"] = float(match.group(1))
    
    return stage_info


def extract_jerseys(soup: BeautifulSoup) -> Dict:
    """استخراج معلومات القمصان من الصفحة."""
    jerseys = {
        "yellow": {"name": "-", "team": "-", "reason": "المتصدر العام"},
        "green": {"name": "-", "team": "-", "reason": "نقاط السبرنت"},
        "polka_dot": {"name": "-", "team": "-", "reason": "متسلق الجبال"},
        "white": {"name": "-", "team": "-", "reason": "أفضل شاب"}
    }
    
    # محاولة استخراج القمصان
    jersey_section = soup.find('div', class_=lambda x: x and 'jersey' in x.lower())
    if jersey_section:
        # استخراج القميص الأصفر
        yellow = jersey_section.find(string=lambda s: s and 'yellow' in s.lower())
        if yellow:
            jerseys["yellow"]["name"] = yellow.parent.find_next('strong').get_text(strip=True) if yellow.parent.find_next('strong') else "-"
    
    return jerseys


def calculate_statistics(results: list) -> Dict:
    """حساب الإحصائيات من النتائج."""
    if not results:
        return {}
    
    teams_count = {}
    for r in results:
        team = r.get("team", "Unknown")
        teams_count[team] = teams_count.get(team, 0) + 1
    
    top_teams = sorted(teams_count.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_participants": len(results),
        "finished": len(results),
        "dnf": 0,
        "average_speed_kmh": 0.0,
        "fastest_avg_kmh": 0.0,
        "youngest_rider": {"name": "-", "age": 0},
        "oldest_rider": {"name": "-", "age": 0},
        "top_teams": [{"name": t[0], "riders": t[1]} for t in top_teams]
    }


def save_to_json(data: Dict, filename: str = OUTPUT_FILE) -> None:
    """حفظ البيانات في ملف JSON."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ تم حفظ البيانات في: {filename}")
    print(f"📊 عدد النتائج: {len(data.get('results', []))}")


def save_error_state(error_message: str, filename: str = OUTPUT_FILE) -> None:
    """حفظ حالة الخطأ في ملف JSON."""
    error_data = {
        "metadata": {
            "race": "Tour de France 2026",
            "last_updated": datetime.now().isoformat(),
            "source": "error",
            "version": "2.0",
            "error": True,
            "error_message": error_message
        },
        "stage": {
            "number": 0,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "no_data",
            "message": "لا توجد بيانات متاحة حالياً"
        },
        "results": [],
        "statistics": {},
        "jerseys": {}
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)
    print(f"⚠️  تم حفظ حالة الخطأ في: {filename}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='جلب بيانات تور دو فرانس 2026 - النسخة الحقيقية')
    parser.add_argument('--stage', type=int, help='رقم المرحلة')
    parser.add_argument('--force', action='store_true', help='إجبار الجلب حتى لو فشل سابقاً')
    parser.add_argument('--output', default=OUTPUT_FILE, help='اسم ملف الإخراج')
    args = parser.parse_args()

    print("=" * 70)
    print("🚴 تور دو فرانس 2026 - جلب البيانات الحقيقية")
    print("=" * 70)
    print()

    # التحقق من المكتبات
    if not HAS_LIBS:
        error_msg = "المكتبات المطلوبة غير مثبتة. يرجى تشغيل: pip install requests beautifulsoup4"
        print(f"❌ {error_msg}")
        save_error_state(error_msg, args.output)
        sys.exit(1)

    # التحقق من الاتصال بالإنترنت
    print("🔍 التحقق من الاتصال بالإنترنت...")
    if not check_internet_connection():
        error_msg = "لا يوجد اتصال بالإنترنت. يرجى التحقق من الاتصال والمحاولة لاحقاً."
        print(f"❌ {error_msg}")
        save_error_state(error_msg, args.output)
        sys.exit(1)
    print("✅ الاتصال بالإنترنت متاح")
    print()

    # التحقق من أن السباق قد بدأ
    print("📅 التحقق من تاريخ السباق...")
    if not check_race_started():
        days_left = (RACE_START_DATE - datetime.now()).days
        error_msg = f"السباق لم يبدأ بعد. يبدأ السباق في 4 يوليو 2026 (متبقي {days_left} يوم). يرجى المحاولة بعد بداية السباق."
        print(f"⏳ {error_msg}")
        save_error_state(error_msg, args.output)
        sys.exit(0)  # خروج طبيعي، ليس خطأ
    print("✅ السباق قد بدأ")
    print()

    # محاولة جلب البيانات من المصادر
    print("🔄 محاولة جلب البيانات من المصادر...")
    print()

    # المحاولة الأولى: الموقع الرسمي
    print("📡 المصدر 1: الموقع الرسمي (letour.fr)")
    data = fetch_from_letour(args.stage)
    
    if data and data.get("results"):
        print("✅ تم جلب البيانات بنجاح من الموقع الرسمي")
        save_to_json(data, args.output)
        print()
        print("🎉 تم بنجاح!")
        sys.exit(0)
    
    print("⚠️  فشل جلب البيانات من الموقع الرسمي")
    print()

    # المحاولة الثانية: ProCyclingStats
    print("📡 المصدر 2: ProCyclingStats")
    data = fetch_from_procyclingstats(args.stage)
    
    if data and data.get("results"):
        print("✅ تم جلب البيانات بنجاح من ProCyclingStats")
        save_to_json(data, args.output)
        print()
        print("🎉 تم بنجاح!")
        sys.exit(0)
    
    print("⚠️  فشل جلب البيانات من ProCyclingStats")
    print()

    # فشل جميع المحاولات
    error_msg = "لم نتمكن من جلب البيانات من أي مصدر. يرجى المحاولة لاحقاً أو التحقق من توفر البيانات."
    print("=" * 70)
    print(f"❌ {error_msg}")
    print("=" * 70)
    print()
    print("💡 نصائح:")
    print("   1. تأكد من أن المرحلة قد انتهت فعلاً")
    print("   2. انتظر بعض الوقت ثم حاول مرة أخرى")
    print("   3. تحقق من توفر البيانات على المواقع الرسمية")
    print("   4. جرب استخدام --force لفرض المحاولة")
    
    save_error_state(error_msg, args.output)
    sys.exit(1)


if __name__ == "__main__":
    main()
