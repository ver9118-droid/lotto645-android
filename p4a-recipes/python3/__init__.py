"""python3 레시피 덮어쓰기: 번들에서 쓰지 않는 표준 라이브러리/C 확장을 제외합니다.

p4a 기본 python3 레시피는 표준 라이브러리 전체와 C 확장 모듈을 번들에 담습니다.
이 앱이 쓰지 않는 것들만 제외해 APK 크기를 줄입니다.

주의: asyncio 와 concurrent 는 제외하면 안 됩니다.
      kivy/clock.py 가 모듈 import 시점에 Clock 인스턴스를 만들고 그 생성자가
      `import asyncio` 를 무조건 실행하므로, 없으면 앱이 시작되지 않습니다.
      (kivy.clock 의 init_async_lib 은 선택 기능이 아닙니다)
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
#   (asyncio/concurrent 는 kivy.clock 이 필요로 하므로 반드시 남긴다)
EXTRA_STDLIB_BLACKLIST = {
    "curses",
    "dbm",
    "pydoc_data",
    "turtledemo",
    "unittest",
    "wsgiref",
    "xml",
    "xmlrpc",
    "_pyrepl",
}

# 번들에서 제외할 C 확장 모듈
#   - CPython 테스트 전용 모듈 (test 패키지는 이미 제외됨)
#   - 서브 인터프리터/원격 디버깅/프로파일링 기능
#   - xml 관련 확장 (xml 표준 라이브러리를 제외하므로 사용되지 않음)
#   - _decimal : Lib/decimal.py 에 _pydecimal 순수 파이썬 폴백이 있어 안전
#   (주의: _asyncio 는 asyncio 표준 라이브러리가 필요로 하므로 남긴다)
EXCLUDED_C_MODULES = {
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
    "_interpchannels",
    "_interpreters",
    "_interpqueues",
    "_lsprof",
    "_remote_debugging",
    "pyexpat",
    "_elementtree",
    "_decimal",
}


class Python3Recipe(_builtin.Python3Recipe):
    stdlib_dir_blacklist = (
        set(_builtin.Python3Recipe.stdlib_dir_blacklist) | EXTRA_STDLIB_BLACKLIST
    )

    def create_python_bundle(self, dirn, arch):
        # 원본이 site-packages 경로를 반환하므로 그대로 돌려줘야 합니다.
        site_packages = super().create_python_bundle(dirn, arch)
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
                removed += os.path.getsize(path)
                os.remove(path)
        if removed:
            info("Removed unused C modules: {:.2f} MB".format(removed / 1048576))

    def get_recipe_dir(self):
        # 패치 파일은 p4a 내장 레시피 폴더에서 찾습니다.
        return os.path.dirname(_BUILTIN)


recipe = Python3Recipe()
