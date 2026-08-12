#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データ変換ロジックのユニットテスト。
非公開APIの仕様変更で convert()/norm_fl() がサイレントに壊れるのを検知する。

実行: python3 -m unittest discover tests -v
"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_haneda import convert
from fetch_aircraft import norm_fl


class TestConvert(unittest.TestCase):
    def sample(self):
        return {
            "airlines": [
                {"flightNumber": "NH060", "airline": "ANA"},
                {"flightNumber": "UA7999", "airline": "United"},
            ],
            "on_time": "10:30",
            "change_time": "10:45",
            "terminal": {"terminal": "2"},
            "status": {"text": "遅延", "reason": "使用機到着遅れ", "category": "delayed"},
            "options": [{"type": "gate", "items": [{"name": "62"}]}],
            "area_name": "札幌(新千歳)",
            "via_area_name": "",
        }

    def test_basic_fields(self):
        f = convert(self.sample(), "dom", "dep", "20260813")
        self.assertEqual(f["fl"], "NH060")
        self.assertEqual(f["al"], "ANA")
        self.assertEqual(f["cs"], ["UA7999"])
        self.assertEqual(f["time"], "10:30")
        self.assertEqual(f["rev"], "10:45")
        self.assertEqual(f["term"], "2")
        self.assertEqual(f["gate"], "62")
        self.assertEqual(f["status"], "遅延")
        self.assertEqual(f["reason"], "使用機到着遅れ")
        self.assertEqual(f["cat"], "delayed")
        self.assertEqual(f["ap"], "札幌(新千歳)")
        self.assertEqual(f["type"], "dep")
        self.assertEqual(f["region"], "dom")
        self.assertEqual(f["date"], "20260813")

    def test_no_change_time_means_empty_rev(self):
        rec = self.sample()
        rec["change_time"] = "10:30"  # 定刻と同じ→変更なし扱い
        self.assertEqual(convert(rec, "dom", "dep", "20260813")["rev"], "")

    def test_international_gate_types(self):
        rec = self.sample()
        rec["options"] = [{"type": "gateDep", "items": [{"name": "141"}]}]
        self.assertEqual(convert(rec, "int", "dep", "20260813")["gate"], "141")

    def test_empty_record_does_not_crash(self):
        f = convert({}, "dom", "arr", "20260813")
        self.assertEqual(f["fl"], "")
        self.assertEqual(f["gate"], "")
        self.assertEqual(f["type"], "arr")

    def test_null_fields_from_api(self):
        # APIがnullを返すパターン（仕様変更時に起きやすい）
        rec = {"airlines": None, "terminal": None, "status": None, "options": None,
               "on_time": None, "change_time": None}
        f = convert(rec, "dom", "dep", "20260813")
        self.assertEqual(f["time"], "")
        self.assertEqual(f["status"], "")


class TestNormFl(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(norm_fl("NH 60"), "NH60")
        self.assertEqual(norm_fl("NH060"), "NH60")
        self.assertEqual(norm_fl("jl123"), "JL123")
        self.assertEqual(norm_fl(""), "")
        self.assertEqual(norm_fl(None), "")
        self.assertEqual(norm_fl("ANA"), "ANA")  # 数字なしはそのまま


if __name__ == "__main__":
    unittest.main()
