[app]
title = 로또 6/45 지능형 추천
package.name = lotto645
package.domain = org.lotto

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json,db,txt,ico,pem
source.exclude_dirs = .buildozer, bin, .git, .github, __pycache__, tests, .venv, .venv-test, .kivy
source.exclude_patterns = *.pyc, *.md, data/lotto.db, data/settings.json, data/recommendations.json, constraints.txt

version = 1.0.0

# Kivy 레시피가 requests 의존성을 끌어옵니다. charset-normalizer 3.5.x 는
# Android 전용 휠을 배포해 p4a 의 pip 설치 단계가 실패하므로 3.4.4 로 고정합니다.
# (실제 고정은 constraints.txt + PIP_CONSTRAINT 로 적용됩니다. p4a 는 여기 적힌
#  버전 표기를 모듈 해석 단계에서 제거하기 때문입니다.)
requirements = python3,kivy,pyjnius,openssl,charset-normalizer==3.4.4

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
