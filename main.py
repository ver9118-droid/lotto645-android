#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""로또 6/45 지능형 추천 — Android(Kivy) 버전.

데스크톱 버전(lotto/app.py)과 동일한 추천 엔진(src/)을 그대로 사용합니다.
화면만 모바일용으로 새로 작성했습니다.
"""

import os
import sys
import json
import threading
import datetime

# ---------------------------------------------------------------------------
# 경로 설정 (Android: 쓰기 가능한 앱 전용 폴더 사용)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if "ANDROID_PRIVATE" in os.environ:                       # p4a 가 설정
    os.environ.setdefault("LOTTO_DATA_DIR", os.environ["ANDROID_PRIVATE"])
sys.path.insert(0, _HERE)

from src import config                                    # noqa: E402
from src.data import storage                              # noqa: E402
from src.analysis import stats as S                       # noqa: E402
from src.recommend import engine as E                     # noqa: E402
from src.updater import Updater                           # noqa: E402

# ---------------------------------------------------------------------------
# Kivy
# ---------------------------------------------------------------------------
from kivy.config import Config                            # noqa: E402
if os.environ.get("KIVY_WINDOW", "") == "" and "ANDROID_PRIVATE" not in os.environ:
    Config.set("graphics", "width", "400")
    Config.set("graphics", "height", "780")
    Config.set("graphics", "resizable", "0")

from kivy.app import App                                  # noqa: E402
from kivy.clock import Clock                              # noqa: E402
from kivy.core.clipboard import Clipboard                 # noqa: E402
from kivy.core.text import LabelBase, DEFAULT_FONT        # noqa: E402
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle  # noqa: E402
from kivy.metrics import dp, sp                           # noqa: E402
from kivy.properties import BooleanProperty, ListProperty  # noqa: E402
from kivy.uix.boxlayout import BoxLayout                  # noqa: E402
from kivy.uix.button import Button                        # noqa: E402
from kivy.uix.floatlayout import FloatLayout              # noqa: E402
from kivy.uix.label import Label as _KivyLabel            # noqa: E402
from kivy.uix.scrollview import ScrollView                # noqa: E402
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition  # noqa: E402
from kivy.uix.spinner import Spinner, SpinnerOption          # noqa: E402
from kivy.uix.textinput import TextInput                  # noqa: E402
from kivy.uix.widget import Widget                        # noqa: E402

# 한글 폰트 (앱 전체 기본 폰트로 등록)
FONT_R = os.path.join(_HERE, "assets", "NanumGothic-Regular.ttf")
FONT_B = os.path.join(_HERE, "assets", "NanumGothic-Bold.ttf")
if os.path.exists(FONT_R):
    LabelBase.register(DEFAULT_FONT, fn_regular=FONT_R,
                       fn_bold=FONT_B if os.path.exists(FONT_B) else FONT_R)


# ---------------------------------------------------------------------------
# 색상 (데스크톱 '다크' 테마와 동일)
# ---------------------------------------------------------------------------
def C(h, a=1.0):
    return (int(h[1:3], 16) / 255.0, int(h[3:5], 16) / 255.0,
            int(h[5:7], 16) / 255.0, a)


PAGE = C("#12161d")
CARD = C("#1e2430")
HEADER = C("#0e1420")
NAV = C("#141922")
FG = C("#e8eef6")
MUTED = C("#93a1b2")
LINE = C("#2c3542")
ACCENT = C("#6fb2ff")
FIELD = C("#2b3546")
HIST = C("#171c25")
PLUS = C("#8d9aa5")

BLUE = C("#2f7fd6")
GREEN = C("#2f9e5f")
PURPLE = C("#7d4fb3")
RED = C("#e74c3c")

BALL_COLORS = [((1, 10), "#FBC400"), ((11, 20), "#69C8F2"), ((21, 30), "#FF7272"),
               ((31, 40), "#AAAAAA"), ((41, 45), "#B0D840")]

STRATEGY_DESC = {
    "balanced": "전체+최근 빈도 균형",
    "hot": "최근 핫 번호 상위 12개 집중",
    "cold": "최근 저빈도(콜드) 번호 우대",
    "frequency": "전체 누적 출현 빈도 기준",
    "recent": "최근 20회 출현 빈도 기준",
    "pattern": "번호 편향 없이 패턴 점수로만 선별 (기본)",
}
STRATEGY_ORDER = ["pattern", "cold", "frequency", "balanced", "recent", "hot"]
STRAT_RANK = {s: i + 1 for i, s in enumerate(STRATEGY_ORDER)}


def ball_rgba(n):
    for (lo, hi), c in BALL_COLORS:
        if lo <= n <= hi:
            return C(c)
    return C("#AAAAAA")


def ball_font(size_px, ratio=0.45):
    """공 지름(px)에 비례하는 글자 크기(sp 단위).

    font_size 는 sp 단위라서 dp 값을 그대로 넣으면 고해상도 단말에서
    글자가 공보다 커집니다. px 목표값을 sp 로 환산합니다.
    """
    return max(7.0, (size_px * ratio) / (sp(1) or 1.0))


def strat_label(name):
    return f"{STRAT_RANK.get(name, 6)}순위 {name}"


def odds_text(n):
    if not n:
        return ""
    per = config.TOTAL_COMBINATIONS / n
    return (f"당첨 확률: {n}/8,145,060 ≈ 1/{per:,.0f}   "
            f"(서로 다른 조합 {n}개)")


# ---------------------------------------------------------------------------
# 공통 위젯
# ---------------------------------------------------------------------------
class Lbl(_KivyLabel):
    """위젯 크기에 맞춰 text_size 를 잡아 halign/valign 이 정상 동작하는 라벨."""

    def __init__(self, **kw):
        kw.pop("text_size", None)
        super().__init__(**kw)
        self.bind(size=self._fit)
        self._fit()

    def _fit(self, *a):
        self.text_size = (self.width, self.height)


class Card(BoxLayout):
    """둥근 배경 카드."""

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", dp(8))
        kw.setdefault("spacing", dp(6))
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self._c = Color(*CARD)
        self._r = RoundedRectangle(radius=[dp(10)])
        self.canvas.before.add(self._c)
        self.canvas.before.add(self._r)
        self.bind(pos=self._sync, size=self._sync)
        self.bind(minimum_height=self.setter("height"))

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class FlatButton(Button):
    """평평한(둥근) 버튼."""

    bg = ListProperty([0.17, 0.21, 0.27, 1])

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_size", sp(13))
        kw.setdefault("color", FG)
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(40))
        super().__init__(**kw)
        self._c = Color(*self.bg)
        self._r = RoundedRectangle(radius=[dp(8)])
        self.canvas.before.add(self._c)
        self.canvas.before.add(self._r)
        self.bind(pos=self._sync, size=self._sync, bg=self._sync_color, state=self._sync_color)
        self._sync()

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size

    def _sync_color(self, *a):
        c = list(self.bg)
        if self.state == "down":
            c = [max(0, v * 0.72) for v in c[:3]] + [c[3]]
        self._c.rgba = c
        self._sync()


class Ball(FloatLayout):
    """단색 로또 공 (숫자 포함)."""

    def __init__(self, number, size=None, **kw):
        s = size or dp(30)
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (s, s))
        super().__init__(**kw)
        with self.canvas.before:
            Color(*ball_rgba(number))
            self._ell = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._pos, size=self._pos)
        self.add_widget(Lbl(text=str(number), font_size=ball_font(s, 0.45), bold=True,
                            color=(1, 1, 1, 1)))
        self._pos()

    def _pos(self, *a):
        self._ell.pos = self.pos
        self._ell.size = self.size


def ball_row(numbers, bonus=None, size=None, spacing=None):
    """번호 배열 → 공 줄."""
    s = size or dp(30)
    row = BoxLayout(orientation="horizontal", size_hint_y=None,
                    height=s + dp(6), spacing=spacing if spacing is not None else dp(5))
    for n in numbers:
        row.add_widget(Ball(n, size=s))
    if bonus is not None:
        row.add_widget(Lbl(text="+", color=PLUS, font_size=ball_font(s, 0.52),
                             size_hint_x=None, width=dp(14)))
        row.add_widget(Ball(bonus, size=s))
    return row


class SetRow(BoxLayout):
    """추천 세트 1줄: 순번 + 공 + 요약."""

    def __init__(self, idx, item, size=None, **kw):
        s = size or dp(29)
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", s + dp(8))
        kw.setdefault("spacing", dp(4))
        super().__init__(**kw)
        self.add_widget(Lbl(text=str(idx), color=MUTED, font_size=sp(11),
                              size_hint_x=None, width=dp(16)))
        for n in item["numbers"]:
            self.add_widget(Ball(n, size=s))
        info = f"{item['score']:.4f}  합{item['sum']}  홀{item['odd_count']}  AC{item['ac']}"
        self.add_widget(Lbl(text=info, color=MUTED, font_size=sp(9.5),
                              halign="right", valign="middle",
                              text_size=(None, None)))


class StatCard(BoxLayout):
    """상단 요약 카드 (제목 + 값)."""

    def __init__(self, title, value="-", color=BLUE, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", dp(6))
        kw.setdefault("spacing", 0)
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(64))
        super().__init__(**kw)
        self._c = Color(*color)
        self._r = RoundedRectangle(radius=[dp(9)])
        self.canvas.before.add(self._c)
        self.canvas.before.add(self._r)
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(Lbl(text=title, color=(1, 1, 1, 0.85), font_size=sp(10.5),
                              size_hint_y=None, height=dp(19), valign="middle"))
        self.value = Lbl(text=str(value), color=(1, 1, 1, 1), bold=True,
                           font_size=sp(17), valign="middle")
        self.add_widget(self.value)

    def set_value(self, v):
        self.value.text = str(v)

    def _sync(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class BarRow(BoxLayout):
    """분석용 가로 막대 한 줄 (라벨 + 막대 + 값)."""

    def __init__(self, label, value, ratio, color=ACCENT, **kw):
        kw.setdefault("orientation", "horizontal")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(22))
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        self.ratio = max(0.0, min(1.0, ratio))
        self._color = color
        self.add_widget(Lbl(text=str(label), color=FG, font_size=sp(11),
                            size_hint_x=None, width=dp(58), halign="center"))
        self.track = Widget()
        self.add_widget(self.track)
        self.add_widget(Lbl(text=str(value), color=MUTED, font_size=sp(10.5),
                            size_hint_x=None, width=dp(46), halign="right"))
        with self.track.canvas.before:
            Color(*LINE)
            self._t = RoundedRectangle(radius=[dp(4)])
        with self.track.canvas.after:
            Color(*self._color)
            self._b = RoundedRectangle(radius=[dp(4)])
        self.track.bind(pos=self._sync, size=self._sync)
        self.bind(pos=self._sync)
        self._sync()

    def _sync(self, *a):
        t = self.track
        self._t.pos = t.pos
        self._t.size = t.size
        w = max(1.0, t.width * self.ratio)
        self._b.pos = t.pos
        self._b.size = (w, t.height)


class ProgressLine(Widget):
    """진행률 얇은 막대 (0.0 ~ 1.0)."""

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(5))
        super().__init__(**kw)
        self.value = 0.0
        with self.canvas.before:
            Color(*LINE)
            self._t = RoundedRectangle(radius=[dp(3)])
        with self.canvas.after:
            Color(*ACCENT)
            self._b = RoundedRectangle(radius=[dp(3)])
        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    def set_value(self, v):
        self.value = max(0.0, min(1.0, v))
        self._sync()

    def _sync(self, *a):
        self._t.pos = self.pos
        self._t.size = self.size
        self._b.pos = self.pos
        self._b.size = (max(0.0, self.width * self.value), self.height)


class Toggle(Widget):
    """플랫 토글 (Kivy Switch 대체 — 다크 테마에 맞춘 단순 디자인)."""

    active = BooleanProperty(False)

    def __init__(self, **kw):
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (dp(46), dp(26)))
        super().__init__(**kw)
        with self.canvas.before:
            self._tc = Color(*C("#39455a"))
            self._track = RoundedRectangle(radius=[self.height / 2.0])
        with self.canvas.after:
            self._kc = Color(1, 1, 1, 1)
            self._knob = Ellipse()
        self.bind(pos=self._sync, size=self._sync, active=self._sync)
        self._sync()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.active = not self.active
            return True
        return super().on_touch_down(touch)

    def _sync(self, *a):
        h = self.height
        r = h / 2.0
        self._track.pos = self.pos
        self._track.size = self.size
        self._track.radius = [r]
        self._tc.rgba = GREEN if self.active else C("#39455a")
        d = h - dp(4)
        cx = (self.right - r) if self.active else (self.x + r)
        self._knob.pos = (cx - d / 2.0, self.center_y - d / 2.0)
        self._knob.size = (d, d)


class DarkOption(SpinnerOption):
    """스피너 드롭다운 항목 (다크 테마)."""

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", C("#26303f"))
        kw.setdefault("color", FG)
        kw.setdefault("font_size", sp(12))
        kw.setdefault("height", dp(32))
        super().__init__(**kw)


class NavButton(FlatButton):
    def __init__(self, text, active=False, **kw):
        kw.setdefault("font_size", sp(12))
        super().__init__(**kw)
        self.text = text
        self.active = active
        self._paint()

    def set_active(self, a):
        self.active = a
        self._paint()

    def _paint(self):
        self.bg = ACCENT if self.active else C("#1a212c")
        self.color = (0.06, 0.08, 0.11, 1) if self.active else MUTED
        self._sync_color()


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
class BaseScreen(Screen):
    """스크롤 + 카드 배치 공통 뼈대."""

    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        root = BoxLayout(orientation="vertical", padding=dp(6), spacing=dp(6))
        sv = ScrollView(do_scroll_x=False)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None,
                             spacing=dp(8), padding=(0, dp(2)))
        self.box.bind(minimum_height=self.box.setter("height"))
        sv.add_widget(self.box)
        root.add_widget(sv)
        self.add_widget(root)

    def section(self, title, extra=None):
        card = Card()
        head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(20),
                         spacing=dp(6))
        head.add_widget(Lbl(text=title, color=FG, bold=True, font_size=sp(12),
                              halign="left", valign="middle",
                              text_size=(None, None)))
        if extra:
            head.add_widget(Lbl(text=extra, color=MUTED, font_size=sp(10),
                                  halign="right", valign="middle",
                                  text_size=(None, None)))
        card.add_widget(head)
        self.box.add_widget(card)
        return card


class HomeScreen(BaseScreen):
    def __init__(self, app, **kw):
        super().__init__(app, name="home", **kw)

        cards = BoxLayout(orientation="horizontal", size_hint_y=None,
                          height=dp(64), spacing=dp(6))
        self.c_total = StatCard("총 수집 회차", "-", BLUE)
        self.c_latest = StatCard("최신 회차", "-", GREEN)
        self.c_date = StatCard("최신 추첨일", "-", PURPLE)
        for c in (self.c_total, self.c_latest, self.c_date):
            cards.add_widget(c)
        self.box.add_widget(cards)

        row = BoxLayout(orientation="horizontal", size_hint_y=None,
                        height=dp(40), spacing=dp(6))
        self.btn_update = FlatButton(text="업데이트", bg=GREEN)
        self.btn_update.bind(on_release=lambda *a: self.app.do_update())
        self.btn_gen = FlatButton(text="추천 생성", bg=C("#2b3546"))
        self.btn_gen.bind(on_release=lambda *a: self.app.do_generate())
        row.add_widget(self.btn_update)
        row.add_widget(self.btn_gen)
        self.box.add_widget(row)

        self.progress = ProgressLine(size_hint_y=None, height=dp(5))
        self.status = Lbl(text="", color=MUTED, font_size=sp(10),
                            size_hint_y=None, height=0, halign="left",
                            text_size=(None, None))
        self.box.add_widget(self.progress)
        self.box.add_widget(self.status)

        self.card_recent = self.section("최근 5회 당첨번호")
        self.card_rec = self.section("추천 5세트", "")
        self.rec_odds = Lbl(text="", color=ACCENT, font_size=sp(10.5),
                              size_hint_y=None, height=0, halign="left",
                              text_size=(None, None))
        self.card_rec.add_widget(self.rec_odds)

    def set_progress(self, value=None, text=None):
        if value is None:
            self.progress.set_value(0)
            self.progress.height = 0
            self.status.height = 0
            self.status.text = ""
        else:
            self.progress.height = dp(5)
            self.progress.set_value(value)
            self.status.height = dp(17)
            self.status.text = text or ""

    def refresh(self):
        draws = storage.get_all_draws()
        self.c_total.set_value(len(draws))
        if draws:
            self.c_latest.set_value(draws[-1].round)
            self.c_date.set_value(draws[-1].date)
        else:
            self.c_latest.set_value("-")
            self.c_date.set_value("-")

        while len(self.card_recent.children) > 1:
            self.card_recent.remove_widget(self.card_recent.children[0])
        for d in draws[-5:]:
            line = BoxLayout(orientation="horizontal", size_hint_y=None,
                             height=dp(32), spacing=dp(4))
            line.add_widget(Lbl(text=f"{d.round}회", color=MUTED, font_size=sp(10),
                                size_hint_x=None, width=dp(50), halign="left"))
            line.add_widget(ball_row(d.numbers, bonus=d.bonus, size=dp(24), spacing=dp(3)))
            self.card_recent.add_widget(line)
        if not draws:
            self.card_recent.add_widget(Lbl(text="데이터 없음 — [업데이트]를 눌러주세요",
                                              color=MUTED, font_size=sp(11),
                                              size_hint_y=None, height=dp(24)))

        # 추천 세트
        while len(self.card_rec.children) > 2:      # 제목 + 확률 라벨 유지
            self.card_rec.remove_widget(self.card_rec.children[0])
        sets = self.app.last_sets
        for i, s in enumerate(sets, 1):
            self.card_rec.add_widget(SetRow(i, s))
        if sets:
            self.rec_odds.height = dp(16)
            self.rec_odds.text = odds_text(len(sets))
        else:
            self.rec_odds.height = dp(16)
            self.rec_odds.text = "추천 생성 버튼을 누르면 표시됩니다."


class RecScreen(BaseScreen):
    def __init__(self, app, **kw):
        super().__init__(app, name="rec", **kw)

        card = Card()
        # 세트 수
        r1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(6))
        r1.add_widget(Lbl(text="세트 수", color=FG, font_size=sp(11.5),
                            size_hint_x=None, width=dp(58)))
        self.sp_sets = Spinner(text="5", values=[str(i) for i in range(1, 11)],
                               size_hint=(None, None), size=(dp(84), dp(32)),
                               background_normal="", background_color=CARD,
                               color=FG, font_size=sp(12), option_cls=DarkOption)
        r1.add_widget(self.sp_sets)
        r1.add_widget(Lbl(text="▼", color=MUTED, font_size=sp(9),
                          size_hint_x=None, width=dp(14)))
        r1.add_widget(Lbl(text="", size_hint_x=1))
        card.add_widget(r1)

        # 전략
        r2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(6))
        r2.add_widget(Lbl(text="전략", color=FG, font_size=sp(11.5),
                            size_hint_x=None, width=dp(58)))
        self.sp_strat = Spinner(text=strat_label(STRATEGY_ORDER[0]),
                                values=[strat_label(s) for s in STRATEGY_ORDER],
                                size_hint=(None, None), size=(dp(190), dp(32)),
                                background_normal="", background_color=CARD,
                                color=FG, font_size=sp(12), option_cls=DarkOption)
        self.sp_strat.bind(text=lambda *a: self._on_strategy())
        r2.add_widget(self.sp_strat)
        r2.add_widget(Lbl(text="▼", color=MUTED, font_size=sp(9),
                          size_hint_x=None, width=dp(14)))
        r2.add_widget(Lbl(text="", size_hint_x=1))
        card.add_widget(r2)

        self.desc = Lbl(text="", color=MUTED, font_size=sp(10),
                          size_hint_y=None, height=dp(14), halign="left",
                          text_size=(None, None))
        card.add_widget(self.desc)

        # 포함 / 제외
        r3 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(6))
        r3.add_widget(Lbl(text="포함", color=FG, font_size=sp(11.5),
                            size_hint_x=None, width=dp(36)))
        self.ti_inc = TextInput(text="", multiline=False, font_size=sp(11.5),
                                background_color=FIELD, foreground_color=FG,
                                cursor_color=ACCENT, padding=[dp(6), dp(6)],
                                size_hint=(None, None), size=(dp(102), dp(32)))
        r3.add_widget(self.ti_inc)
        r3.add_widget(Lbl(text="제외", color=FG, font_size=sp(11.5),
                            size_hint_x=None, width=dp(36)))
        self.ti_exc = TextInput(text="", multiline=False, font_size=sp(11.5),
                                background_color=FIELD, foreground_color=FG,
                                cursor_color=ACCENT, padding=[dp(6), dp(6)],
                                size_hint=(None, None), size=(dp(102), dp(32)))
        r3.add_widget(self.ti_exc)
        r3.add_widget(Lbl(text="", size_hint_x=1))
        card.add_widget(r3)
        self.box.add_widget(card)

        # 인기 회피
        card2 = Card()
        r4 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(4))
        r4.add_widget(Lbl(text="공동당첨 위험 최소화 (인기번호 회피)",
                          color=FG, font_size=sp(11), halign="left"))
        self.sw_anti = Toggle(active=False)
        r4.add_widget(self.sw_anti)
        card2.add_widget(r4)
        self.box.add_widget(card2)

        self.btn_gen = FlatButton(text="번호 생성", bg=BLUE, height=dp(44))
        self.btn_gen.bind(on_release=lambda *a: self.app.do_generate())
        self.box.add_widget(self.btn_gen)

        self.card_res = self.section("결과", "")
        self.res_odds = Lbl(text="", color=ACCENT, font_size=sp(10.5),
                              size_hint_y=None, height=dp(16), halign="left",
                              text_size=(None, None))
        self.card_res.add_widget(self.res_odds)
        self.holder = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.holder.bind(minimum_height=self.holder.setter("height"))
        self.card_res.add_widget(self.holder)

        btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(42),
                         spacing=dp(6))
        b_copy = FlatButton(text="복사", bg=C("#2b3546"))
        b_copy.bind(on_release=lambda *a: self.app.copy_results())
        b_share = FlatButton(text="공유(카톡 등)", bg=GREEN)
        b_share.bind(on_release=lambda *a: self.app.share_results())
        btns.add_widget(b_copy)
        btns.add_widget(b_share)
        self.box.add_widget(btns)

        self.status = Lbl(text="", color=ACCENT, font_size=sp(10),
                          size_hint_y=None, height=0, halign="left",
                          text_size=(None, None))
        self.box.add_widget(self.status)

        self._on_strategy()
        self.refresh()

    def set_status(self, msg=None):
        if msg:
            self.status.text = msg
            self.status.height = dp(18)
        else:
            self.status.text = ""
            self.status.height = 0

    def _on_strategy(self):
        name = self.app.current_strategy(self.sp_strat.text)
        rank = STRAT_RANK.get(name, 1)
        self.desc.text = f"{rank}순위 전략 — {STRATEGY_DESC.get(name, '')}"

    def refresh(self):
        self.holder.clear_widgets()
        sets = self.app.last_sets
        for i, s in enumerate(sets, 1):
            self.holder.add_widget(SetRow(i, s))
        self.res_odds.text = odds_text(len(sets)) if sets else "아직 생성하지 않았습니다."


class AnalysisScreen(BaseScreen):
    def __init__(self, app, **kw):
        super().__init__(app, name="analysis", **kw)

        cards = BoxLayout(orientation="horizontal", size_hint_y=None,
                          height=dp(64), spacing=dp(6))
        self.c_sum = StatCard("평균 합계", "-", BLUE)
        self.c_ac = StatCard("평균 AC", "-", GREEN)
        self.c_odd = StatCard("홀짝(평균)", "-", PURPLE)
        for c in (self.c_sum, self.c_ac, self.c_odd):
            cards.add_widget(c)
        self.box.add_widget(cards)

        self.card_hot = self.section("HOT 15 (최근 50회)")
        self.card_cold = self.section("COLD 15 (최근 50회)")
        self.card_freq = self.section("번호별 출현 빈도", "")
        self.freq_holder = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(1))
        self.freq_holder.bind(minimum_height=self.freq_holder.setter("height"))
        self.card_freq.add_widget(self.freq_holder)

    @staticmethod
    def _ball_lines(nums, per_row=8, size=None):
        """HOT/COLD 15개를 화면 폭에 맞춰 2줄로 배치."""
        s = size or dp(26)
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        box.bind(minimum_height=box.setter("height"))
        for i in range(0, len(nums), per_row):
            row = BoxLayout(orientation="horizontal", size_hint_y=None,
                            height=s + dp(4), spacing=dp(4))
            for n in nums[i:i + per_row]:
                row.add_widget(Ball(n, size=s))
            box.add_widget(row)
        return box

    def refresh(self):
        draws = storage.get_all_draws()
        if not draws:
            return
        sm = S.summary(draws)
        self.c_sum.set_value(f"{sm.get('avg_sum', 0):.1f}")
        self.c_ac.set_value(f"{sm.get('avg_ac', 0):.1f}")
        odd = sm.get('avg_odd')
        self.c_odd.set_value(f"{odd:.1f}" if isinstance(odd, (int, float)) else "-")

        hot = S.hot_numbers(draws, top=15)
        cold = S.cold_numbers(draws, top=15)
        for card, nums in ((self.card_hot, hot), (self.card_cold, cold)):
            while len(card.children) > 1:
                card.remove_widget(card.children[0])
            if nums:
                card.add_widget(self._ball_lines(nums))

        freq = S.frequency(draws)
        top = max(freq) if freq else 1
        self.freq_holder.clear_widgets()
        order = sorted(range(45), key=lambda i: -freq[i])
        for i in order:
            n = i + 1
            self.freq_holder.add_widget(
                BarRow(n, freq[i], freq[i] / top if top else 0,
                       color=ball_rgba(n)[:3]))


class SettingsScreen(BaseScreen):
    def __init__(self, app, **kw):
        super().__init__(app, name="settings", **kw)

        card = Card()
        r1 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(6))
        r1.add_widget(Lbl(text="자동 업데이트", color=FG, font_size=sp(11.5),
                          halign="left"))
        self.sw_auto = Toggle(active=True)
        self.sw_auto.bind(active=lambda *a: self.app.on_auto_change())
        r1.add_widget(self.sw_auto)
        card.add_widget(r1)

        r2 = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(34),
                       spacing=dp(6))
        r2.add_widget(Lbl(text="간격(시간)", color=FG, font_size=sp(11.5),
                            size_hint_x=None, width=dp(72)))
        self.sp_interval = Spinner(text="6", values=[str(i) for i in range(1, 25)],
                                   size_hint=(None, None), size=(dp(84), dp(32)),
                                   background_normal="", background_color=CARD,
                                   color=FG, font_size=sp(12), option_cls=DarkOption)
        self.sp_interval.bind(text=lambda *a: self.app.on_auto_change())
        r2.add_widget(self.sp_interval)
        r2.add_widget(Lbl(text="▼", color=MUTED, font_size=sp(9),
                          size_hint_x=None, width=dp(14)))
        r2.add_widget(Lbl(text="", size_hint_x=1))
        card.add_widget(r2)

        btn = FlatButton(text="지금 업데이트", bg=GREEN, height=dp(40))
        btn.bind(on_release=lambda *a: self.app.do_update())
        card.add_widget(btn)
        self.box.add_widget(card)

        self.status = Lbl(text="", color=ACCENT, font_size=sp(10),
                          size_hint_y=None, height=0, halign="left",
                          text_size=(None, None))
        self.box.add_widget(self.status)

        card2 = self.section("데이터")
        self.l_info = Lbl(text="", color=MUTED, font_size=sp(11),
                            size_hint_y=None, height=dp(46), halign="left",
                            valign="top", text_size=(None, None))
        card2.add_widget(self.l_info)
        btn2 = FlatButton(text="데이터 다시 받기 (전체 재수집)", bg=C("#2b3546"))
        btn2.bind(on_release=lambda *a: self.app.reseed())
        card2.add_widget(btn2)

        card3 = self.section("앱 정보")
        self.l_about = Lbl(
            text=("로또 6/45 지능형 추천  v1.0 (Android)\n"
                  "추천 엔진: 백테스트 커버리지 기준 1~6순위 전략\n"
                  "데이터: 동행복권 공식 회차 (미러 자동 동기화)\n\n"
                  "1등 확률은 조합당 1/8,145,060으로 고정이며,\n"
                  "서로 다른 조합 수를 늘리는 것만이 확률을 올립니다.\n"
                  "이 앱은 참고용이며 당첨을 보장하지 않습니다."),
            color=MUTED, font_size=sp(10.5), size_hint_y=None, height=dp(150),
            halign="left", valign="top", text_size=(None, None))
        card3.add_widget(self.l_about)

    def set_status(self, msg=None):
        if msg:
            self.status.text = msg
            self.status.height = dp(18)
        else:
            self.status.text = ""
            self.status.height = 0

    def refresh(self):
        latest = storage.get_latest_round()
        cnt = storage.count_draws()
        self.l_info.text = (f"보유 회차: {cnt}회  |  최신: {latest}회\n"
                            f"데이터 폴더: {config.DATA_DIR}")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class LottoApp(App):
    title = "로또 6/45 지능형 추천"
    last_sets = ListProperty([])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.settings = {}          # 평범한 dict (스레드에서도 안전)

    # ---------- 설정 ----------
    def load_settings(self):
        try:
            with open(config.SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"auto_update": True, "interval_hours": 6}

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(config.SETTINGS_PATH), exist_ok=True)
            with open(config.SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- 화면 ----------
    def build(self):
        self.settings = self.load_settings()
        storage.init_db()
        self._seed_bundled()
        self._load_last_sets()

        self.updater = Updater(progress_cb=self._on_upd_progress,
                               log_cb=self._on_log)
        self.busy = False

        if os.environ.get("ANDROID_PRIVATE"):
            from kivy.core.window import Window
            Window.softinput_mode = "below_target"
            Window.bind(on_keyboard=self._on_android_back)

        root = BoxLayout(orientation="vertical")
        head = BoxLayout(orientation="horizontal", size_hint_y=None,
                         height=dp(46), padding=(dp(10), 0), spacing=dp(6))
        with head.canvas.before:
            Color(*HEADER)
            head_bg = Rectangle(pos=head.pos, size=head.size)
        head.bind(pos=lambda *a: setattr(head_bg, "pos", head.pos),
                  size=lambda *a: setattr(head_bg, "size", head.size))
        head.add_widget(Lbl(text="로또 6/45  지능형 추천", color=FG, bold=True,
                              font_size=sp(14), halign="left", valign="middle",
                              text_size=(None, None)))
        self.head_info = Lbl(text="", color=MUTED, font_size=sp(10),
                               halign="right", valign="middle",
                               text_size=(None, None))
        head.add_widget(self.head_info)
        root.add_widget(head)

        self.sm = ScreenManager(transition=NoTransition())
        self.home = HomeScreen(self)
        self.rec = RecScreen(self)
        self.analysis = AnalysisScreen(self)
        self.settings_screen = SettingsScreen(self)
        for s in (self.home, self.rec, self.analysis, self.settings_screen):
            self.sm.add_widget(s)
        root.add_widget(self.sm)

        self.nav = BoxLayout(orientation="horizontal", size_hint_y=None,
                             height=dp(54), spacing=dp(6), padding=(dp(6), dp(5)))
        with self.nav.canvas.before:
            Color(*NAV)
            nav_bg = Rectangle(pos=self.nav.pos, size=self.nav.size)
        self.nav.bind(pos=lambda *a: setattr(nav_bg, "pos", self.nav.pos),
                      size=lambda *a: setattr(nav_bg, "size", self.nav.size))
        self.nav_btns = {}
        for key, label in (("home", "홈"), ("rec", "추천"),
                           ("analysis", "분석"), ("settings", "설정")):
            b = NavButton(label, active=(key == "home"))
            b.bind(on_release=lambda inst, k=key: self.goto(k))
            self.nav_btns[key] = b
            self.nav.add_widget(b)
        root.add_widget(self.nav)

        # 초기 반영
        s = self.settings
        self.settings_screen.sw_auto.active = bool(s.get("auto_update", True))
        self.settings_screen.sp_interval.text = str(int(s.get("interval_hours", 6)))
        self.rec.sp_sets.text = str(int(s.get("sets", config.DEFAULT_SETS)))
        self.rec.sp_strat.text = strat_label(s.get("strategy", STRATEGY_ORDER[0]))
        self.rec.sw_anti.active = bool(s.get("anti_popular", False))
        self.rec._on_strategy()
        Clock.schedule_once(lambda *a: self.refresh_all(), 0.1)
        Clock.schedule_once(lambda *a: self.after_start(), 0.6)
        return root

    # ---------- 데이터 ----------
    def _seed_bundled(self):
        """앱에 포함된 draws.json 으로 첫 실행 시 DB 채우기 (오프라인 대비)."""
        if storage.count_draws() > 0:
            return
        bundled = os.path.join(_HERE, "data", "draws.json")
        if os.path.exists(bundled):
            try:
                n = storage.import_json(bundled)
                print(f"[seed] bundled draws imported: {n}")
            except Exception as e:
                print("[seed] failed:", e)

    def _load_last_sets(self):
        try:
            with open(config.RECOMMENDATIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.last_sets = data.get("sets", [])
        except Exception:
            self.last_sets = []

    def after_start(self):
        if self.settings.get("auto_update", True):
            self.updater.start_background(float(self.settings.get("interval_hours", 6)))

    def current_strategy(self, label=None):
        text = label if label is not None else self.rec.sp_strat.text
        for s in STRATEGY_ORDER:
            if text.endswith(s):
                return s
        return STRATEGY_ORDER[0]

    @staticmethod
    def _parse_nums(text):
        out = []
        for tok in (text or "").replace(" ", "").split(","):
            if tok:
                n = int(tok)
                if 1 <= n <= 45 and n not in out:
                    out.append(n)
        return out

    # ---------- 진행 표시 ----------
    @staticmethod
    def _fmt_status(text):
        t = (text or "").strip()
        return t if len(t) <= 44 else t[:41] + "..."

    def _set_busy(self, value, text=None):
        self.busy = value
        self.home.btn_update.disabled = value
        self.home.btn_gen.disabled = value
        self.rec.btn_gen.disabled = value

    def _on_upd_progress(self, cur, total, ok=True):
        r = (cur / total) if total else 0
        Clock.schedule_once(lambda *a: self.home.set_progress(
            r, f"업데이트 중... {cur}/{total} ({r * 100:.0f}%)"))

    def _on_log(self, msg):
        print("[log]", msg)
        Clock.schedule_once(lambda *a: self.home.set_progress(
            1.0, self._fmt_status(msg)) if self.busy else None)

    # ---------- 액션 ----------
    def do_update(self):
        if self.busy:
            return
        self._set_busy(True)
        self.home.set_progress(0, "업데이트 확인 중...")

        def work():
            try:
                added = self.updater.update_now()
                msg = f"{added}개 회차 추가됨" if added else "최신 상태입니다"
            except Exception as e:
                msg = f"오류: {e}"
            Clock.schedule_once(lambda *a: self._after_update(msg))

        threading.Thread(target=work, daemon=True).start()

    def _after_update(self, msg):
        self._set_busy(False)
        self.home.set_progress(1.0, msg)
        self.settings_screen.set_status(msg)
        Clock.schedule_once(lambda *a: (self.home.set_progress(None),
                                        self.settings_screen.set_status(None)), 2.5)
        self.refresh_all()

    def reseed(self):
        if self.busy:
            return
        self._set_busy(True)
        self.home.set_progress(0.3, "전체 데이터 재수집 중...")

        def work():
            try:
                from src.data import fetcher
                storage.init_db()
                draws = fetcher.seed_from_mirror()
                storage.upsert_draws(draws)
                storage.export_json()
                msg = f"전체 {len(draws)}회차 재수집 완료"
            except Exception as e:
                msg = f"오류: {e}"
            Clock.schedule_once(lambda *a: self._after_update(msg))

        threading.Thread(target=work, daemon=True).start()

    def do_generate(self):
        if self.busy:
            return
        draws = storage.get_all_draws()
        if not draws:
            self.toast("데이터가 없습니다. 먼저 업데이트하세요.")
            return
        try:
            n_sets = int(self.rec.sp_sets.text)
            include = self._parse_nums(self.rec.ti_inc.text)
            exclude = self._parse_nums(self.rec.ti_exc.text)
        except ValueError:
            self.toast("입력 오류: 숫자를 쉼표로 구분해 입력하세요.")
            return
        if len(include) > 6:
            self.toast("포함 번호는 최대 6개까지 입력할 수 있습니다.")
            return
        if set(include) & set(exclude):
            self.toast("포함 번호와 제외 번호가 겹칩니다.")
            return
        strategy = self.current_strategy()
        anti = bool(self.rec.sw_anti.active)

        self._set_busy(True)
        self.home.set_progress(0, "번호 생성 중...")

        def work():
            try:
                def prog(done, total):
                    Clock.schedule_once(lambda *a: self.home.set_progress(
                        done / total, f"번호 생성 중... {done}/{total} ({done / total * 100:.0f}%)"))
                sets = E.generate_sets(draws, n_sets=n_sets, strategy=strategy,
                                       include=include, exclude=exclude,
                                       anti_popular=anti, progress_cb=prog)
                if sets:
                    self._save_sets(sets, strategy, n_sets, anti)
                msg = None if sets else "조건에 맞는 조합이 없습니다. 포함/제외 번호를 조정해 주세요."
                Clock.schedule_once(lambda *a: self._after_generate(sets, msg))
            except Exception as e:
                Clock.schedule_once(lambda *a: self._after_generate([], str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _save_sets(self, sets, strategy, n_sets, anti):
        try:
            os.makedirs(os.path.dirname(config.RECOMMENDATIONS_PATH), exist_ok=True)
            with open(config.RECOMMENDATIONS_PATH, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.datetime.now().isoformat(),
                           "strategy": strategy, "sets": sets}, f,
                          ensure_ascii=False, indent=2)
        except Exception:
            pass
        st = dict(self.settings)
        st.update({"sets": int(n_sets), "strategy": strategy,
                   "anti_popular": bool(anti)})
        self.settings = st
        self.save_settings()

    def _after_generate(self, sets, err=None):
        self._set_busy(False)
        if sets:
            self.last_sets = sets
        msg = err if err else f"{len(sets)}세트 생성 완료"
        self.home.set_progress(1.0, msg)
        self.rec.set_status(msg)
        Clock.schedule_once(lambda *a: (self.home.set_progress(None),
                                        self.rec.set_status(None)), 2.5)
        self.refresh_all()
        if sets:
            self.goto("home")

    def copy_results(self):
        text = self._result_text()
        if not text:
            return
        Clipboard.copy(text)
        self.toast("클립보드에 복사했습니다")

    def share_results(self):
        text = self._result_text()
        if not text:
            return
        if os.environ.get("ANDROID_PRIVATE"):
            try:
                from jnius import autoclass, cast
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                String = autoclass("java.lang.String")
                intent = Intent()
                intent.setAction(Intent.ACTION_SEND)
                intent.setType("text/plain")
                intent.putExtra(Intent.EXTRA_TEXT,
                                cast("java.lang.CharSequence", String(text)))
                chooser = Intent.createChooser(
                    intent, cast("java.lang.CharSequence", String("번호 공유")))
                PythonActivity.mActivity.startActivity(chooser)
                return
            except Exception as e:
                print("[share] failed:", e)
        Clipboard.copy(text)
        self.toast("공유를 지원하지 않아 클립보드에 복사했습니다")

    def _result_text(self):
        if not self.last_sets:
            self.toast("먼저 번호를 생성하세요")
            return ""
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"로또 6/45 추천  {stamp}"]
        for i, s in enumerate(self.last_sets, 1):
            lines.append(f"{i}. " + " ".join(f"{n:02d}" for n in s["numbers"]))
        lines.append("")
        lines.append(odds_text(len(self.last_sets)))
        return "\n".join(lines)

    def toast(self, msg):
        self.home.set_progress(1.0, msg)
        self.rec.set_status(msg)

        def clear(*a):
            self.home.set_progress(None)
            self.rec.set_status(None)

        Clock.schedule_once(clear, 2.2)

    def on_auto_change(self):
        st = dict(self.settings)
        st["auto_update"] = bool(self.settings_screen.sw_auto.active)
        try:
            st["interval_hours"] = int(self.settings_screen.sp_interval.text)
        except ValueError:
            st["interval_hours"] = 6
        self.settings = st
        self.save_settings()
        self.updater.stop()
        if st["auto_update"]:
            self.updater.start_background(float(st["interval_hours"]))

    # ---------- 공통 ----------
    def _on_android_back(self, window, key, scancode, codepoint, modifier):
        """안드로이드 뒤로가기: 다른 탭이면 홈으로, 홈이면 앱 종료."""
        if key == 27 and self.sm.current != "home":
            self.goto("home")
            return True
        return False

    def goto(self, key):
        self.sm.current = key
        for k, b in self.nav_btns.items():
            b.set_active(k == key)
        if key == "analysis":
            self.analysis.refresh()
        elif key == "settings":
            self.settings_screen.refresh()
        elif key == "rec":
            self.rec.refresh()
        elif key == "home":
            self.home.refresh()

    def refresh_all(self):
        self.home.refresh()
        self.rec.refresh()
        latest = storage.get_latest_round()
        cnt = storage.count_draws()
        self.head_info.text = f"{cnt}회차 · 최신 {latest}회" if latest else "데이터 없음"
        if self.sm.current == "analysis":
            self.analysis.refresh()
        if self.sm.current == "settings":
            self.settings_screen.refresh()


if __name__ == "__main__":
    LottoApp().run()
