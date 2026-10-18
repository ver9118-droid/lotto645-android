"""Configuration and constants for the Korean Lotto 6/45 recommender."""

import os
import sys

APP_NAME = "Korean Lotto 6/45 Intelligent Recommender"
APP_VERSION = "1.0.0"

_override = os.environ.get("LOTTO_DATA_DIR")
if _override:
    # Android 등 쓰기 가능한 앱 전용 폴더 (main.py에서 지정)
    BASE_DIR = _override
elif getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "lotto.db")
DRAWS_JSON_PATH = os.path.join(DATA_DIR, "draws.json")
RECOMMENDATIONS_PATH = os.path.join(DATA_DIR, "recommendations.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
LOG_PATH = os.path.join(DATA_DIR, "app.log")

# HTTPS 인증서 검증용 CA 번들 (앱에 포함; Android에는 시스템 CA 저장소가 없음)
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CA_BUNDLE_PATH = os.path.join(APP_ROOT, "assets", "cacert.pem")

LOTTO_MIN = 1
LOTTO_MAX = 45
NUMBERS_PER_DRAW = 6
TOTAL_COMBINATIONS = 8145060

DHLOTTERY_DETAIL_URL = "https://www.dhlottery.co.kr/lt645/selectPstLt645Info.do"
MIRROR_LATEST_URL = "https://smok95.github.io/lotto/results/latest.json"
MIRROR_ALL_URL = "https://smok95.github.io/lotto/results/all.json"

DRAW_WEEKDAY = 5
DRAW_HOUR = 20
DRAW_MINUTE = 45

RECENT_WINDOW = 20
HOT_COLD_WINDOW = 50

DEFAULT_SETS = 5
DEFAULT_STRATEGY = "balanced"

SUM_MIN = 95
SUM_MAX = 190
AC_MIN = 7
AC_MAX = 10
ODD_COUNTS_ALLOWED = (2, 3, 4)
HIGH_COUNTS_ALLOWED = (2, 3, 4)
MAX_CONSECUTIVE_PAIRS = 2
MIN_DISTINCT_ZONES = 4

ZONES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 45)]

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    pass
