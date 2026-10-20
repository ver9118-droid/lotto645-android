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
#   - CPython 테스트 전용 모듈 (test 패키지는 이미 제외됨)
#   - 서브 인터프리터/원격 디버깅/프로파일링 등 사용하지 않는 기능
#   - 표준 라이브러리에서 이미 제외한 모듈의 C 확장 (_asyncio, pyexpat 등)
#   - decimal : Lib/decimal.py 에 _pydecimal 폴백이 있어 안전함
#   - CJK 코덱: cp949(한국어)는 _codecs_kr 를 쓰므로 유지, 일본/중국/대만만 제외
EXCLUDED_C_MODULES = {
    # 테스트 전용
    "_ctypes_test",
    "_testbuffer",
    "_testcapi",
    "_testclinic",
    "_testclinic_limited",
    "_testimportmultiple",
    "_testinternalcapi",
    "_testlimitedcapi",
    "_testmultiphase",
    "_testsinglephase",
    "_xxtestfuzz",
    "xxlimited",
    "xxlimited_35",
    "xxsubtype",
    # 사용하지 않는 기능
    "_interpchannels",
    "_interpreters",
    "_interpqueues",
    "_lsprof",
    "_remote_debugging",
    # 표준 라이브러리에서 제외한 모듈의 C 확장
    "_asyncio",
    "_elementtree",
    "pyexpat",
    # 순수 파이썬 폴백이 있는 모듈
    "_decimal",
    # 일본/중국/대만 코덱 (한국어 cp949 는 유지)
    "_codecs_cn",
    "_codecs_hk",
    "_codecs_jp",
    "_codecs_tw",
}


class Python3Recipe(_builtin.Python3Recipe):
    stdlib_dir_blacklist = (
        set(_builtin.Python3Recipe.stdlib_dir_blacklist) | EXTRA_STDLIB_BLACKLIST
    )

    def create_python_bundle(self, dirn, arch):
        super().create_python_bundle(dirn, arch)
        self._drop_c_modules(dirn)

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
