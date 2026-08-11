#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flights_data.js の各便に「機材（機種）」を付与する。
データ元: AeroDataBox (RapidAPI 無料枠)。羽田公式ダイヤには機種が無いため補完に使う。

前提:
  1) 先に  python3 fetch_haneda.py  を実行して flights_data.js を作っておく
  2) RapidAPI で AeroDataBox の無料プラン(Basic)に登録し、APIキーを取得
     https://rapidapi.com/aedbx-aedbx/api/aerodatabox → Subscribe → Basic(無料)
  3) キーを環境変数か key.txt で渡す:
        export AERODATABOX_KEY="xxxxxxxx"
     もしくは このフォルダに  aerodatabox_key.txt  を置き、中にキーだけ書く

使い方:
    python3 fetch_aircraft.py

仕組み:
  空港の発着一覧エンドポイント(1回で12時間ぶん・機種入り)を、
  flights_data.js に含まれる日付×[00-12,12-24]の窓ぶん呼ぶ(1日=2回)。
  返ってきた便名→機種を、便名+時刻で羽田公式データに突合して actype を書き込む。
  無料枠(月700回)に対し 2日分でも4回程度なので十分収まる。
"""
import json, os, re, sys, time, urllib.request, urllib.error, datetime

HOST = "aerodatabox.p.rapidapi.com"
DATA_JS = "flights_data.js"


def get_key():
    k = os.environ.get("AERODATABOX_KEY", "").strip()
    if k:
        return k
    for fn in ("aerodatabox_key.txt", "key.txt"):
        if os.path.exists(fn):
            return open(fn, encoding="utf-8").read().strip()
    return ""


def load_data():
    txt = open(DATA_JS, encoding="utf-8").read()
    m = re.search(r"window\.HND_FLIGHTS\s*=\s*(\{.*\});?\s*$", txt, re.S)
    if not m:
        sys.exit("flights_data.js を解析できません。先に fetch_haneda.py を実行してください。")
    return json.loads(m.group(1))


def norm_fl(s):
    """便名を突合キーに正規化: 空白除去→英字部+数字(先頭0除去)。 'NH 60'→'NH60', 'NH060'→'NH60'"""
    if not s:
        return ""
    s = s.upper().replace(" ", "")
    m = re.match(r"([A-Z]+)0*([0-9]+)", s)
    return f"{m.group(1)}{m.group(2)}" if m else s


def api_window(key, frm, to):
    """RJTT の frm..to(ローカル時刻, 最大12h)の発着を取得し {便名norm: 機種} を返す"""
    url = (f"https://{HOST}/flights/airports/Icao/RJTT/"
           f"{frm}/{to}?withLeg=false&withCancelled=true&withCodeshared=false"
           f"&withCargo=true&withPrivate=false&withLocation=false")
    req = urllib.request.Request(url, headers={
        "X-RapidAPI-Key": key,
        "X-RapidAPI-Host": HOST,
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    out = {}
    for side in ("departures", "arrivals"):
        for f in d.get(side, []) or []:
            num = norm_fl(f.get("number", ""))
            model = ((f.get("aircraft") or {}).get("model")) or ""
            if num and model:
                out[num] = model
    return out


def windows_for_day(day):
    """YYYYMMDD -> [(from,to), ...] 12時間ずつ(ISOローカル 'YYYY-MM-DDThh:mm')"""
    d = datetime.datetime.strptime(day, "%Y%m%d")
    base = d.strftime("%Y-%m-%d")
    return [(f"{base}T00:00", f"{base}T11:59"),
            (f"{base}T12:00", f"{base}T23:59")]


def main():
    key = get_key()
    if not key:
        print("APIキーが見つかりません。次のいずれかで設定してください:")
        print('  export AERODATABOX_KEY="あなたのキー"')
        print("  または aerodatabox_key.txt にキーを保存")
        print("\n無料キーの取得: https://rapidapi.com/aedbx-aedbx/api/aerodatabox （Basic=無料）")
        sys.exit(1)

    data = load_data()
    days = data.get("days") or [data.get("date")]
    model_map = {}
    calls = 0
    for day in days:
        for frm, to in windows_for_day(day):
            try:
                mp = api_window(key, frm, to)
                model_map.update(mp)
                calls += 1
                print(f"  {frm}〜{to}: {len(mp)}便に機種")
                time.sleep(1.0)
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:200]
                print(f"  {frm}〜{to}: HTTP {e.code} {body}")
                if e.code in (401, 403):
                    sys.exit("APIキーが無効、または未サブスクライブです。RapidAPIでBasicプランに登録してください。")
                if e.code == 429:
                    sys.exit("無料枠の上限に達しました。翌月まで待つか、プランを確認してください。")
            except Exception as e:
                print(f"  {frm}〜{to}: 失敗 {type(e).__name__} {e}")

    # 突合して actype を書き込む
    hit = 0
    for f in data["flights"]:
        model = model_map.get(norm_fl(f.get("fl", "")))
        if model:
            f["actype"] = model
            hit += 1
        else:
            f.setdefault("actype", "")

    data["aircraftFetchedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    js = "// 自動生成: fetch_haneda.py + fetch_aircraft.py\n" \
         "window.HND_FLIGHTS = " + json.dumps(data, ensure_ascii=False) + ";\n"
    open(DATA_JS, "w", encoding="utf-8").write(js)
    print(f"\n✅ 機種を付与しました: {hit}/{len(data['flights'])}便（API呼び出し {calls}回）")
    print("   index.html を再読み込みしてください。")


if __name__ == "__main__":
    main()
