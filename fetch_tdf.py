#!/usr/bin/env python3
"""
سكربت جلب بيانات تور دو فرانس 2026
يجلب بيانات المرحلة المنتهية ويحفظها في results.json

الاستخدام:
    python fetch_tdf.py              # جلب تلقائي
    python fetch_tdf.py --stage 5    # جلب مرحلة محددة
    python fetch_tdf.py --demo       # بيانات تجريبية للاختبار

المتطلبات:
    pip install requests beautifulsoup4
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  تحذير: لم يتم تثبيت requests/beautifulsoup4. سيتم استخدام البيانات التجريبية.")
    print("   للتثبيت: pip install requests beautifulsoup4")


# ============ إعدادات ============
OUTPUT_FILE = "results.json"
TDF_2026_URL = "https://www.letour.fr/en/overall-ranking"
PROCYCLINGSTATS_URL = "https://www.procyclingstats.com/race/tour-de-france/2026/"

# رؤوس طلب لتجنب الحجب
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml"
}


def generate_demo_data(stage_number: int = 1) -> Dict:
    """
    يولّد بيانات تجريبية واقعية لاختبار الواجهة.
    استخدم هذه الدالة قبل بداية السباق (4 يوليو 2026) أو كـ fallback.
    """
    # بيانات الدراجين الأوائل (واقعية)
    top_riders = [
        {"rank": 1, "rider": "Tadej Pogačar", "team": "UAE Team Emirates XRG", "country": "SLO", "bib": 1, "time": "0:22:15", "gap": "0:00", "age": 27, "points": 50},
        {"rank": 2, "rider": "Jonas Vingegaard", "team": "Visma–Lease a Bike", "country": "DEN", "bib": 11, "time": "0:22:23", "gap": "+0:08", "age": 28, "points": 30},
        {"rank": 3, "rider": "Remco Evenepoel", "team": "Red Bull–Bora–Hansgrohe", "country": "BEL", "bib": 21, "time": "0:22:29", "gap": "+0:14", "age": 25, "points": 20},
        {"rank": 4, "rider": "Matteo Jorgenson", "team": "Visma–Lease a Bike", "country": "USA", "bib": 14, "time": "0:22:35", "gap": "+0:20", "age": 25, "points": 18},
        {"rank": 5, "rider": "Brandon McNulty", "team": "UAE Team Emirates XRG", "country": "USA", "bib": 4, "time": "0:22:41", "gap": "+0:26", "age": 27, "points": 16},
        {"rank": 6, "rider": "Primož Roglič", "team": "Red Bull–Bora–Hansgrohe", "country": "SLO", "bib": 22, "time": "0:22:44", "gap": "+0:29", "age": 35, "points": 14},
        {"rank": 7, "rider": "Carlos Rodríguez", "team": "INEOS Grenadiers", "country": "ESP", "bib": 31, "time": "0:22:48", "gap": "+0:33", "age": 24, "points": 12},
        {"rank": 8, "rider": "João Almeida", "team": "UAE Team Emirates XRG", "country": "POR", "bib": 2, "time": "0:22:52", "gap": "+0:37", "age": 26, "points": 10},
        {"rank": 9, "rider": "Mattias Skjelmose", "team": "Lidl-Trek", "country": "DEN", "bib": 51, "time": "0:22:56", "gap": "+0:41", "age": 24, "points": 8},
        {"rank": 10, "rider": "Ben Healy", "team": "EF Education-EasyPost", "country": "IRL", "bib": 71, "time": "0:23:02", "gap": "+0:47", "age": 24, "points": 6},
    ]

    # توليد بقية الدراجين (174 دراج)
    import random
    countries = ["FRA", "ITA", "ESP", "GER", "NED", "BEL", "GBR", "AUS", "COL", "USA", "SUI", "NOR", "POL", "AUT"]
    teams = ["Groupama-FDJ", "Soudal Quick-Step", "Bahrain Victorious", "Movistar Team", "Jayco AlUla",
             "Cofidis", "Team TotalEnergies", "Uno-X Mobility", "Alpecin-Premier Tech", "Decathlon CMA CGM"]
    
    for i in range(11, 185):
        minutes = 23 + (i // 20)
        seconds = random.randint(0, 59)
        gap_seconds = (i - 1) * 3 + random.randint(0, 10)
        gap_min = gap_seconds // 60
        gap_sec = gap_seconds % 60
        
        top_riders.append({
            "rank": i,
            "rider": f"Rider #{i}",
            "team": random.choice(teams),
            "country": random.choice(countries),
            "bib": 100 + i,
            "time": f"0:{minutes:02d}:{seconds:02d}",
            "gap": f"+{gap_min}:{gap_sec:02d}",
            "age": random.randint(21, 38),
            "points": max(0, 50 - i)
        })

    # بيانات المرحلة
    stage_info = {
        "number": stage_number,
        "date": f"2026-07-{3 + stage_number:02d}",
        "start": "Barcelona" if stage_number == 1 else f"City {stage_number}",
        "end": "Barcelona" if stage_number == 1 else f"City {stage_number}",
        "distance_km": 19.7 if stage_number == 1 else 180 + random.randint(-20, 30),
        "type": "TTT" if stage_number == 1 else random.choice(["flat", "hilly", "mountain"]),
        "status": "completed",
        "weather": "مشمس، 24°C" if random.random() > 0.5 else "غائم جزئياً، 21°C"
    }

    return {
        "metadata": {
            "race": "Tour de France 2026",
            "edition": 113,
            "last_updated": datetime.now().isoformat(),
            "source": "demo_data",
            "version": "1.0"
        },
        "stage": stage_info,
        "results": top_riders,
        "statistics": {
            "total_participants": 184,
            "finished": 182,
            "dnf": 2,
            "average_speed_kmh": 53.2,
            "fastest_avg_kmh": 53.8,
            "youngest_rider": {"name": "Paul Seixas", "age": 20},
            "oldest_rider": {"name": "Primož Roglič", "age": 35}
        },
        "jerseys": {
            "yellow": {"name": "Tadej Pogačar", "team": "UAE Team Emirates XRG", "reason": "المتصدر العام"},
            "green": {"name": "Tadej Pogačar", "team": "UAE Team Emirates XRG", "reason": "نقاط السبرنت"},
            "polka_dot": {"name": "Jonas Vingegaard", "team": "Visma–Lease a Bike", "reason": "متسلق الجبال"},
            "white": {"name": "Remco Evenepoel", "team": "Red Bull–Bora–Hansgrohe", "reason": "أفضل شاب"}
        }
    }


def fetch_live_data(stage_number: Optional[int] = None) -> Dict:
    """
    يجلب البيانات الحقيقية من مصادر الويب.
    ملاحظة: تور دو فرانس 2026 لم يبدأ بعد، لذا يتم استخدام البيانات التجريبية حالياً.
    """
    if not HAS_REQUESTS:
        print("⚠️  لا يمكن جلب البيانات بدون requests. استخدام البيانات التجريبية.")
        return generate_demo_data(stage_number or 1)

    # في الوقت الحالي (قبل 4 يوليو 2026) لا توجد بيانات حقيقية
    print("📅 السباق لم يبدأ بعد (يبدأ 4 يوليو 2026)")
    print("🔄 استخدام البيانات التجريبية للتدريب...")
    return generate_demo_data(stage_number or 1)

    # ============ الكود التالي سيفعّل بعد بداية السباق ============
    # try:
    #     response = requests.get(TDF_2026_URL, headers=HEADERS, timeout=10)
    #     response.raise_for_status()
    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     
    #     # استخراج البيانات من الصفحة (التنسيق الفعلي يعتمد على بنية الموقع)
    #     results = []
    #     table = soup.find('table', class_='results-table')
    #     if table:
    #         rows = table.find_all('tr')[1:]  # تخطي رأس الجدول
    #         for i, row in enumerate(rows, 1):
    #             cols = row.find_all('td')
    #             if len(cols) >= 4:
    #                 results.append({
    #                     "rank": i,
    #                     "rider": cols[1].text.strip(),
    #                     "team": cols[2].text.strip(),
    #                     "time": cols[3].text.strip(),
    #                     "gap": cols[4].text.strip() if len(cols) > 4 else "0:00"
    #                 })
    #     
    #     return {
    #         "metadata": {
    #             "race": "Tour de France 2026",
    #             "last_updated": datetime.now().isoformat(),
    #             "source": "letour.fr"
    #         },
    #         "results": results
    #     }
    # except Exception as e:
    #     print(f"❌ خطأ في جلب البيانات: {e}")
    #     print("🔄 استخدام البيانات التجريبية كبديل...")
    #     return generate_demo_data(stage_number or 1)


def save_to_json(data: Dict, filename: str = OUTPUT_FILE) -> None:
    """يحفظ البيانات في ملف JSON مع ترميز UTF-8."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ تم حفظ البيانات في: {filename}")
    print(f"📊 عدد النتائج: {len(data.get('results', []))}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='جلب بيانات تور دو فرانس 2026')
    parser.add_argument('--stage', type=int, help='رقم المرحلة (افتراضي: 1)')
    parser.add_argument('--demo', action='store_true', help='استخدام بيانات تجريبية')
    parser.add_argument('--output', default=OUTPUT_FILE, help='اسم ملف الإخراج')
    args = parser.parse_args()

    print("=" * 60)
    print("🚴 تور دو فرانس 2026 - جلب البيانات")
    print("=" * 60)

    if args.demo:
        print("🧪 وضع البيانات التجريبية")
        data = generate_demo_data(args.stage or 1)
    else:
        data = fetch_live_data(args.stage)

    save_to_json(data, args.output)
    print("🎉 تم بنجاح!")


if __name__ == "__main__":
    main()
