"""python3 레시피 덮어쓰기: 번들에 필요 없는 표준 라이브러리와 자산을 제외합니다.

p4a 기본 python3 레시피는 표준 라이브러리 전체와 site-packages 를 그대로
번들(_python_bundle)에 담습니다. 이 앱이 실제로 쓰지 않는 것들은
stdlib_dir_blacklist / site_packages_dir_blacklist 에 추가해 APK 크기를 줄입니다.

빌드 방법/패치는 빌드 컨테이너에 들어 있는 python-for-android 기본
레시피를 그대로 재사용합니다.
"""
import glob
import importlib.util
import os

import pythonforandroid

from pythonforandroid.logger import info

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

# site-packages 안의 불필요한 항목은 Kivy 레시피(p4a-recipes/kivy)의
# postbuild_arch 에서 개별 파일 단위로 정리합니다.
# (kivy/data/fonts 전체를 빼면 kivy.core.text 의 import 시점 폰트 등록이
#  IOError 로 실패하므로 디렉터리 단위 제외는 하지 않습니다.)


# 번들에서 제외할 C 확장 모듈
#   (현재 비활성화)
#   Android 런타임에서 어떤 모듈이 interpreter 가 필요로 하는지 확정하기 어려워
#   C 확장 모듈은 남겨둔다. 제외했던 목록:
#     - CPython 테스트 전용 모듈 (_testcapi 등)
#     - 서브 인터프리터/원격 디버깅/프로파일링 기능
#     - _asyncio, pyexpat, _elementtree (표준 라이브러리에서 이미 제외)
#     - _decimal (Lib/decimal.py 에 _pydecimal 폴백이 있어 안전함)
#     - 일본/중국/대만 CJK 코덱 (cp949 는 _codecs_kr 로 유지)
EXCLUDED_C_MODULES: set[str] = set()


class Python3Recipe(_builtin.Python3Recipe):
    stdlib_dir_blacklist = (
        set(_builtin.Python3Recipe.stdlib_dir_blacklist) | EXTRA_STDLIB_BLACKLIST
    )

    def create_python_bundle(self, dirn, arch):
        # 원본이 site-packages 경로를 반환하므로 그대로 돌려줘야 합니다.
        site_packages = super().create_python_bundle(dirn, arch)
        if EXCLUDED_C_MODULES:
            self._drop_c_modules(dirn)
        return site_packages

    def _drop_c_modules(self, dirn):
        """번들에서 쓰지 않는 C 확장 모듈을 지웁니다."""
        modules_dir = os.path.join(dirn, "modules")
        if not os.path.isdir(modules_dir):
            return
        removed = 0
        for name in sorted(EXCLUDED_C_MODULES):
            for path in glob.glob(os.path.join(modules_dir, name + ".*")):
                size = os.path.getsize(path)
                os.remove(path)
                removed += size
        if removed:
            info("Removed unused C modules: {:.2f} MB".format(removed / 1048576))

    def get_recipe_dir(self):
        # 패치 파일은 p4a 내장 레시피 폴더에서 찾습니다.
        return os.path.dirname(_BUILTIN)


recipe = Python3Recipe()
