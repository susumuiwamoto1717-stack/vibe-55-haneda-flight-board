# vibe-55 羽田空港 発着案内板（滑走路予測つき）

羽田空港の発着を「空港の発着掲示板（FIDS）」スタイルで見るローカルWebアプリ。
定期ダイヤを羽田公式から自動取得し、**風向き・時間帯から滑走路（A/B/C/D）を予測**して表示する。
スポッター（飛行機を見る人）向けに、滑走路別に離着陸をまとめて見られる。

作成: 2026-07-01〜07-03 / 羽田空港での実利用がきっかけ。

---

## ファイル構成
| ファイル | 役割 |
|---|---|
| `index.html` | アプリ本体（単一HTML・掲示板UI・滑走路予測・配置図・全ロジック） |
| `fetch_haneda.py` | 羽田公式APIから当日＋翌日のダイヤを取得し `flights_data.js` を生成 |
| `fetch_aircraft.py` | AeroDataBox(RapidAPI無料枠)で各便に機種を付与（キー必要） |
| `flights_data.js` | 取得済みダイヤ（自動生成 / `window.HND_FLIGHTS`） |
| `server.py` | ローカルサーバー。画面の「🔄 更新」ボタンで最新取得を可能にする |
| `auto_update.sh` | 一定間隔で自動取得し続ける常駐スクリプト |

## 起動方法（推奨：サーバー経由）
```bash
cd vibe-55-haneda-flight-board
python3 server.py          # → http://localhost:8787 を開く（停止 Ctrl+C）
```
- 右上「🔄 更新」で最新ダイヤを取得して再表示
- `file://` で直接 index.html を開くと更新ボタンは使えない（案内が出る）

### 自動更新（任意）
```bash
bash auto_update.sh        # 10分ごと取得（引数で秒数変更: bash auto_update.sh 300）
```
画面は5分ごとに自動リロード（タブ/フィルタ/風向は保持）。

### 機材（機種）を出す（任意）
AeroDataBox の無料キーが必要（羽田公式に機種が無いため）。
1. https://rapidapi.com/aedbx-aedbx/api/aerodatabox → Basic(無料)をSubscribe
2. `export AERODATABOX_KEY="キー"` または `aerodatabox_key.txt` に保存
3. `python3 fetch_aircraft.py`（server.py/auto_update.sh経由なら自動で併走）

---

## 主な機能
- **掲示板UI**: 黒地×アンバー、ライブ時計、ARRIVALS/DEPARTURES/RUNWAY の3ビュー
- **滑走路予測（RWY）**: 北風/南風/南風15–19時の新ルートを公開ルールで判定し、便ごとに割当（2本並ぶ時は「目安」）
- **滑走路別ビュー**: A/B/C/D を選ぶと、その滑走路の離陸🛫と着陸🛬が時刻順に混在表示。ボタンに役割（着/発/着発/－）を表示
- **配置図**: 「🗺 滑走路の配置図」で自作SVGの配置図（本土/東京湾/方位つき、使用中を着色、選択中を太枠、タップで一覧へ）
- **日跨ぎ12時間窓**: 基準時刻から12時間先まで、翌日分も続けて表示
- **状況表示**: 欠航=赤行+理由、遅延=公式判定のみ（早発/微調整は定刻扱い）、出発済/到着済はグレー
- **航空会社名**: 3レターコードを日本語名に変換（主要50社超）

---

## 羽田公式フライトAPI（非公開・リバースエンジニアリング済）
`fetch_haneda.py` が使用。**キー不要**。
- `POST https://tokyo-haneda.com/app/api/v2/flight/search`
- 必須ヘッダ: `Content-Type: application/json`, `X-Requested-With: XMLHttpRequest`,
  `Origin: https://tokyo-haneda.com`, `Referer: https://tokyo-haneda.com/flight/flightInfo_dms.html`, ブラウザ風UA。無いと403。
- body: `{"flightType":1|2,"arrivalType":1|2,"searchDt":"YYYYMMDD","airportCodes":[],"airlineCodes":[],"flightNumber":"","status":[]}`
  - flightType 1=国内/2=国際、arrivalType 1=出発/2=到着、status は必ず空配列 `[]`
- レスポンス `flightlists[]`: area_name(相手都市)/airlines[].{airline,flightNumber}/on_time(定刻)/change_time(変更)/terminal.terminal/status.{text,category,reason}/options(gate等)
- 当日 国内+国際で計 約1,300便。

**注意**: これは羽田の非公開エンドポイント。個人〜小規模利用向け。公開時は低頻度サーバー取得＋キャッシュ配信で配慮すること。

## 滑走路運用ルール（国交省「羽田空港のこれから」ベース）
- 滑走路: A=16R/34L, B=04/22, C=16L/34R, D=05/23（R/Lは平行2本A/Cの左右区別。各滑走路は物理1本で、番号は使用方向）
- 南風 15–19時（新ルート）: 着陸 C(16L)/A(16R)、出発 A(16R)/B(22)
- 南風 その他: 着陸 B(22)/D(23)、出発 C(16L)/A(16R)
- 北風: 着陸 A(34L)/C(34R)、出発 D(05)/C(34R)
- 便ごとの2本振り分けは目安（管制判断）。

## わかったこと（データの性質）
- **欠航/遅延の判定はアプリではなく羽田公式のstatus.category/textをそのまま表示**。真偽は公式更新に追従。
- **欠航・遅延の理由は運航時刻に近づくと埋まる（事後的）**。先の未来便は理由が空。→ 見たい時間帯に近いタイミングで更新するのがコツ。
- 日跨ぎ深夜便は提供元により出発日/到着日の枠割当が異なり、古いスナップショットだと実態とズレる。
- **機長名は非公開**でどのデータ源にも無い（クルーロスターは航空会社の社内情報）。
- OpenSky無料APIは2025年から認証必須で403。adsb.lolはキー不要だがairborne便のみ＆ブラウザからはCORSで直叩き不可。

---

## 今後（未着手）
- **Vercel + Supabase での一般公開**: Supabase Edge Function（pg_cron）で羽田を10–15分ごと取得→`flights`テーブルにupsert→Vercelのフロントが読むだけ。取得を1か所に集約（CORS/礼儀/速度）。機材キーはSupabase Secret。
- METAR自動取得で風向自動判定、機材APIの実キー検証。
