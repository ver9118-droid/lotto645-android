"""이 앱용 Kivy 레시피 덮어쓰기.

p4a 기본 Kivy 레시피는 python_depends 로
certifi, chardet, idna, requests, urllib3, filetype 를 설치합니다.
이 앱은 HTTP 를 표준 라이브러리(src/data/fetcher.py)로 처리하고
kivy.network.urlrequest 를 쓰지 않으므로 위 패키지가 전혀 필요 없습니다.
(그대로 두면 APK 에 약 3.5MB 의 불필요한 파일이 들어갑니다.)

소스 URL/버전, 패치, 빌드 환경은 빌드 컨테이너에 들어 있는
python-for-android 기본 레시피를 그대로 재사용합니다.
"""
import importlib.util
import os

import pythonforandroid

_BUILTIN = os.path.join(
    os.path.dirname(pythonforandroid.__file__), "recipes", "kivy", "__init__.py"
)

_spec = importlib.util.spec_from_file_location("_p4a_builtin_kivy", _BUILTIN)
_builtin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builtin)


class KivyRecipe(_builtin.KivyRecipe):
    # setuptools 는 Kivy 빌드에만 쓰이고 런타임에는 필요 없습니다.
    # (Python 3.14 번들에는 pkg_resources 가 없고,
    #  pyjnius 도 3.9+ 에서는 importlib.resources 를 사용합니다.)
    depends = [('sdl2', 'sdl3'), 'pyjnius', 'android']

    # filetype: kivy/core/image 에서 필수
    # certifi  : Android 에서 원격 이미지 로딩(loader.py) 시 사용
    # requests/chardet/idna/urllib3 는 이 앱에서 쓰지 않으므로 제외
    python_depends = ['filetype', 'certifi']

    def get_recipe_dir(self):
        # 패치 파일(use_cython.patch 등)은 p4a 내장 레시피 폴더에서 찾습니다.
        return os.path.dirname(_BUILTIN)


recipe = KivyRecipe()
