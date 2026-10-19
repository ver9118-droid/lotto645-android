[app]
title = 로또 6/45 지능형 추천
package.name = lotto645
package.domain = org.lotto

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,db,txt,ico,pem
source.exclude_dirs = .buildozer, bin, .git, .github, __pycache__, tests, .venv, .venv-test, .kivy
source.exclude_patterns = *.pyc, *.md, data/lotto.db, data/settings.json, data/recommendations.json

version = 1.0.0

requirements = python3,kivy,pyjnius,openssl

orientation = portrait
fullscreen = 0
android.allow_backup = True

icon.filename = %(source.dir)s/assets/icon.png
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
