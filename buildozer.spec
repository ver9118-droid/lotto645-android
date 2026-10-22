[app]
title = 로또 6/45 지능형 추천
package.name = lotto645
package.domain = org.lotto

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,db,txt,ico,pem
source.exclude_dirs = .buildozer, bin, .git, .github, __pycache__, tests, .venv, .venv-test, .kivy, font_src, tools, p4a-recipes
source.exclude_patterns = *.pyc, *.md, data/lotto.db, data/settings.json, data/recommendations.json, constraints.txt, assets/icon*.png, assets/presplash.png

version = 1.1.0

# Kivy 기본 의존성 중 requests 계열은 p4a-recipes/kivy 에서 제외했습니다.
requirements = python3,kivy,pyjnius,openssl

# Kivy 레시피 덮어쓰기(불필요한 pip 의존성 제거) 위치
p4a.local_recipes = %(source.dir)s/p4a-recipes

orientation = portrait
fullscreen = 0
android.allow_backup = True

icon.filename = %(source.dir)s/assets/icon.png
# Android 8.0+ 적응형 아이콘(런처가 모양을 잘라내므로 전경/배경을 따로 줍니다)
icon.adaptive_foreground.filename = %(source.dir)s/assets/icon_fg.png
icon.adaptive_background.filename = %(source.dir)s/assets/icon_bg.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #12161d

android.permissions = INTERNET
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

android.logcat_filters = *:S python:D

[buildozer]
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
