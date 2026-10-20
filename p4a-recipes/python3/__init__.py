"""python3 레시피 덮어쓰기: 번들에 필요 없는 표준 라이브러리와 자산을 제외합니다.

p4a 기본 python3 레시피는 표준 라이브러리 전체와 site-packages 를 그대로
번들(_python_bundle)에 담습니다. 이 앱이 실제로 쓰지 않는 것들은
stdlib_dir_blacklist / site_packages_dir_blacklist 에 추가해 APK 크기를 줄입니다.

빌드 방법/패치는 빌드 컨테이너에 들어 있는 python-for-android 기본
레시피를 그대로 재사용합니다.
"""
import importlib.util
import os

import pythonforandroid

_BUILTIN = os.path.join(
    os.path.dirname(pythonforandroid.__file__), "recipes", "python3", "__init__.py"
)

_spec = importlib.util.spec_from_file_location("_p4a_builtin_python3", _BUILTIN)
_builtin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builtin)

# 이 앱이 쓰지 않는 표준 라이브러리
#   asyncio/concurrent : Kivy 의 선택적 async API 용 (기본 경로에서 미사용)
#   unittest            : 테스트 전용
#   pydoc_data/_pyrepl  : help()/대화형 REPL 전용
#   xml                 : plistlib/xmlrpc 용 (미사용)
EXTRA_STDLIB_BLACKLIST = {
    "asyncio",
    "concurrent",
    "curses",
    "dbm",
    "multiprocessing",
    "pydoc_data",
    "turtledemo",
    "unittest",
    "wsgiref",
    "xml",
    "xmlrpc",
    "_pyrepl",
}

# site-packages 안의 불필요한 디렉터리
#   fonts : Kivy 내장 Roboto/DejaVu 폰트 (기본 폰트는 NanumGothic 으로 교체)
#   tools : Kivy 개발/패키징 도구
EXTRA_SITE_PACKAGES_BLACKLIST = {
    "fonts",
    "tools",
}


class Python3Recipe(_builtin.Python3Recipe):
    stdlib_dir_blacklist = (
        set(_builtin.Python3Recipe.stdlib_dir_blacklist) | EXTRA_STDLIB_BLACKLIST
    )
    site_packages_dir_blacklist = (
        set(_builtin.Python3Recipe.site_packages_dir_blacklist)
        | EXTRA_SITE_PACKAGES_BLACKLIST
    )

    def get_recipe_dir(self):
        # 패치 파일은 p4a 내장 레시피 폴더에서 찾습니다.
        return os.path.dirname(_BUILTIN)


recipe = Python3Recipe()
