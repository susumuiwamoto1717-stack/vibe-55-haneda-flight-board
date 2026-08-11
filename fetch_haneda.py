#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
羽田空港 公式フライト情報APIから当日の定期便ダイヤを取得し、
アプリが読み込む flights_data.js を生成する。

使い方:
    python3 fetch_haneda.py            # 今日+翌日の2日分を取得(日跨ぎ表示用)
    python3 fetch_haneda.py 20260702   # 指定日から2日分
    python3 fetch_haneda.py 20260702 3 # 指定日から3日分

出力: flights_data.js  ( window.HND_FLIGHTS = [...] )
     index.html を開くと自動で最新ダイヤが反映される。

データ元: tokyo-haneda.com（羽田空港旅客ターミナル 公式）非公開の内部APIを利用。
仕様変更で動かなくなる可能性あり。個人利用の範囲で。
"""
import urllib.request, json, time, sys, datetime

API = "https://tokyo-haneda.com/app/api/v2/flight/search"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://tokyo-haneda.com",
    "Referer": "https://tokyo-haneda.com/flight/flightInfo_dms.html",
    "Accept": "application/json",
}

# flightType: 1=国内, 2=国際 / arrivalType: 1=出発, 2=到着
CATS = [
    (1, 1, "dom", "dep"),
    (1, 2, "dom", "arr"),
    (2, 1, "int", "dep"),
    (2, 2, "int", "arr"),
]


def call(flight_type, arrival_type, search_dt):
    body = {
        "flightType": flight_type,
        "arrivalType": arrival_type,
        "searchDt": search_dt,
        "airportCodes": [],
        "airlineCodes": [],
        "flightNumber": "",
        "status": [],
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def convert(rec, region, direction, day):
    airlines = rec.get("airlines") or [{}]
    fl = airlines[0].get("flightNumber", "")
    al = airlines[0].get("airline", "") or ""   # 航空会社名（例: JAL, ANA）
    # 共同運航（コードシェア）便名を併記
    codeshare = [a.get("flightNumber", "") for a in airlines[1:] if a.get("flightNumber")]
    on = rec.get("on_time", "") or ""
    chg = rec.get("change_time", "") or ""
    term = ""
    t = rec.get("terminal") or {}
    if isinstance(t, dict):
        term = t.get("terminal", "") or ""
    status, reason, category = "", "", ""
    s = rec.get("status") or {}
    if isinstance(s, dict):
        status = s.get("text", "") or ""       # 出発済み / 欠航 / 遅延 など
        reason = s.get("reason", "") or ""      # 欠航・遅延の理由
        category = s.get("category", "") or ""  # departed / canceled / delayed ...
    # ゲート番号（搭乗口）を options から抽出
    # 国内線は type=gate、国際線は type=gateDep(出発)/gateArr(到着)
    gate = ""
    for opt in (rec.get("options") or []):
        if isinstance(opt, dict) and opt.get("type") in ("gate", "gateDep", "gateArr"):
            items = opt.get("items") or []
            if items:
                gate = items[0].get("name", "") or ""
            break
    return {
        "type": "arr" if direction == "arr" else "dep",
        "region": region,                 # dom / int
        "date": day,                      # YYYYMMDD（この便の日付）
        "time": on,                       # 定刻
        "rev": chg if chg and chg != on else "",  # 変更時刻(あれば)
        "fl": fl,
        "al": al,                         # 航空会社名
        "cs": codeshare,                  # コードシェア便名
        "ap": rec.get("area_name", ""),   # 相手空港（都市名）
        "via": rec.get("via_area_name", ""),
        "term": term,                     # ターミナル
        "gate": gate,                     # 搭乗口
        "status": status,                 # 遅延/欠航など
        "reason": reason,                 # 欠航・遅延の理由
        "cat": category,                  # departed/canceled/delayed...
    }


def fetch_metar():
    """羽田(RJTT)の実況気象から風向・風速を取得（aviationweather.gov・キー不要）。
    失敗しても None を返すだけでダイヤ取得は続行する。"""
    url = "https://aviationweather.gov/api/data/metar?ids=RJTT&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        if data:
            m = data[0]
            return {
                "wdir": m.get("wdir"),          # 風向（度・磁方位）
                "wspd": m.get("wspd"),          # 風速（kt）
                "raw": m.get("rawOb", ""),
                "reportTime": m.get("reportTime", ""),
            }
    except Exception as e:
        print(f"  METAR取得失敗（風向は手動設定のまま）: {type(e).__name__} {e}")
    return None


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d")
    ndays = int(sys.argv[2]) if len(sys.argv) > 2 else 2  # 既定=今日+翌日
    start_d = datetime.datetime.strptime(start, "%Y%m%d")
    days = [(start_d + datetime.timedelta(days=i)).strftime("%Y%m%d") for i in range(ndays)]

    all_flights = []
    for day in days:
        print(f"[{day}]")
        for ft, at, region, direction in CATS:
            try:
                d = call(ft, at, day)
                fl = d.get("flightlists") or []
                for rec in fl:
                    all_flights.append(convert(rec, region, direction, day))
                print(f"  {region} {direction}: {len(fl)}件")
                time.sleep(0.4)
            except Exception as e:
                print(f"  {region} {direction}: 取得失敗 {type(e).__name__} {e}")

    # 日付+時刻順にソート
    def sk(f):
        return (f["date"], 0 if f["type"] == "arr" else 1, f["time"] or "99:99")
    all_flights.sort(key=sk)

    metar = fetch_metar()
    if metar:
        print(f"  METAR: 風向{metar['wdir']}° 風速{metar['wspd']}kt")

    payload = {
        "date": start,
        "days": days,
        "fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(all_flights),
        "metar": metar,
        "flights": all_flights,
    }
    js = "// 自動生成: fetch_haneda.py\n" \
         "window.HND_FLIGHTS = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    with open("flights_data.js", "w", encoding="utf-8") as f:
        f.write(js)
    print(f"\n✅ flights_data.js を生成しました（{len(all_flights)}便 / {'〜'.join([days[0], days[-1]])}）")
    print("   index.html を開けば最新ダイヤが反映されます。")


if __name__ == "__main__":
    main()
