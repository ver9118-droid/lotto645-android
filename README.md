# 로또 6/45 지능형 추천 (Android)

데스크톱 버전(Windows)과 **동일한 추천 엔진**을 사용하는 안드로이드 앱입니다.
화면(UI)만 Kivy로 새로 작성했고, 추천 로직·점수 계산·데이터 처리는 그대로 재사용합니다.

## 기능

- **홈** — 총 수집 회차 / 최신 회차 / 최신 추첨일, 최근 5회 당첨번호(공 스타일), 추천 5세트
- **추천** — 세트 수(1~10), 전략(1순위~6순위), 포함/제외 번호, 공동당첨 위험 최소화(인기번호 회피)
- **분석** — 평균 합계·AC·홀짝, HOT/COLD 15개, 번호별 출현 빈도(45개 막대)
- **설정** — 자동 업데이트 on/off·간격, 데이터 정보, 전체 재수집
- **공유** — 안드로이드 공유 시트로 카카오톡 등에 바로 전송

## 추천 전략 순위

백테스트(최근 200회차 × 3시드 = 600표본) 평균 커버리지 기준:

| 순위 | 전략 | 설명 |
|---|---|---|
| 1순위 | pattern | 번호 편향 없이 패턴 점수로만 선별 (기본) |
| 2순위 | cold | 최근 저빈도(콜드) 번호 우대 |
| 3순위 | frequency | 전체 누적 출현 빈도 |
| 4순위 | balanced | 전체+최근 빈도 균형 |
| 5순위 | recent | 최근 20회 출현 빈도 |
| 6순위 | hot | 최근 핫 번호 상위 12개 집중 |

## 확률에 대한 정직한 안내

1등 확률은 **조합당 1/8,145,060으로 고정**입니다. 서로 다른 조합 N개면 N/8,145,060이며,
이 앱은 항상 **서로 다른 조합만** 생성합니다. 확률을 실제로 올리는 방법은 조합 수를 늘리는 것뿐이고,
인기번호 회피는 당첨 시 **나눠갖는 사람 수**를 줄이는 역할입니다.

## 빌드 (GitHub Actions)

`.github/workflows/build-apk.yml` 이 공식 `kivy/buildozer` 도커 이미지로 APK를 만듭니다.
`main` 브랜치에 푸시하거나 Actions 탭에서 수동 실행하면 `lotto645-apk` 아티팩트로 APK가 올라옵니다.

로컬(리눅스/도커)에서 빌드하려면:

```bash
docker run --rm -v "$PWD":/home/user/hostcwd \
  -v "$HOME/.buildozer":/home/user/.buildozer \
  -e PIP_CONSTRAINT=/home/user/hostcwd/constraints.txt \
  ghcr.io/kivy/buildozer:latest android debug
```

`-e PIP_CONSTRAINT=...` 는 안전장치입니다. p4a 가 (다른 경로로) `requests` 를 다시
끌어오면 `charset-normalizer` 최신 버전의 Android 전용 휠을 골라 호스트 pip 설치가
실패할 수 있습니다(`not a supported wheel on this platform`). `constraints.txt` 로
순수 휠(`py3-none-any`)이 있는 3.4.4 를 강제해 둡니다.

## 화면 수정 이력 (휴대폰 실기기 기준)

- **공 숫자 표시** — `Label.font_size` 는 픽셀 단위인데 `sp(1)` 로 나눠서 값을 넘기고 있었습니다.
  데스크톱(density 1)에서는 우연히 맞았지만 휴대폰(density 3)에서는 공의 15% 크기로 그려져
  보이지 않았습니다. 픽셀 단위로 계산하도록 고치고, 숫자는 자식 Label 이 아니라 캔버스에
  직접 렌더하도록 바꿨습니다(ScrollView 안에서 텍스트가 그려지지 않던 문제도 함께 해결).
- **스크롤바 겹침** — Kivy 의 `ScrollView` 세로 스크롤바가 내용 위에 겹쳐 그려져
  분석 화면의 오른쪽 값 열을 가렸습니다. 스크롤바 폭을 줄이고 콘텐츠 여백을 두었습니다.
- **크래시 진단** — 시작 중 예외가 나면 앱이 죽지 않고 **화면에 traceback** 을 보여주고,
  `crash.log` 로 저장합니다(`/sdcard/Android/data/org.lotto.lotto645/files/crash.log`).

> **주의**: `asyncio` 와 `concurrent` 표준 라이브러리는 **절대로 번들에서 제외하면 안 됩니다.**
> `kivy/clock.py` 가 모듈 import 시점에 `Clock` 인스턴스를 만들고, 그 생성자가
> `init_async_lib()` → `import asyncio` 를 **무조건** 실행합니다.
> 없으면 `import kivy` 단계에서 `ImportError` 가 나 앱이 바로 죽습니다
> (Presplash 만 잠깐 보이다 사라지는 증상). 선택 기능이 아닙니다.
>
> 참고로 `kivy.clock` 의 `init_async_lib` 는 Kivy 의 선택적 async API 를 위한
> 코드처럼 보이지만, `Clock` 생성자에서 기본값으로 호출되므로 사실상 필수입니다.

## APK 크기 최적화

디버그 APK 기준 **22.31 MB → 16.63 MB** (약 25% 감소) 했습니다.

> **현재 상태**: 실기기에서 동작이 확인된 최적화만 적용되어 있습니다.
> (requests 계열 제거, 폰트 서브셋, 적응형 아이콘, setuptools 제거,
>  Kivy 내장 도구·미사용 폰트 제거, 표준 라이브러리 9종 제외, 불필요한 C 확장 22개 제외)

- **불필요한 파이썬 패키지 제거** — `p4a-recipes/kivy` 가 Kivy 기본
  `python_depends`(requests, chardet, idna, urllib3)를 설치하지 않습니다.
  이 앱은 HTTP 를 표준 라이브러리로 처리하고 `kivy.network.urlrequest` 를 쓰지 않습니다.
  (`filetype` 은 `kivy/core/image` 가 시작 시 import 하므로 유지, `certifi` 는
  Android 원격 이미지 로딩 경로용으로 유지)
- **setuptools 제거** — 빌드에만 필요하고 런타임에는 쓰이지 않아 `depends` 에서 뺍니다.
  Python 3.14 번들에는 `pkg_resources` 가 없고 pyjnius 도 3.9+ 에서는 `importlib.resources` 를 씁니다.
- **표준 라이브러리 정리** — `p4a-recipes/python3` 가 `stdlib_dir_blacklist` 를 확장해
  이 앱이 쓰지 않는 모듈(asyncio, unittest, multiprocessing, xml, pydoc_data 등)을 번들에서 뺍니다.
- **불필요한 C 확장 모듈 제거** — 같은 레시피가 번들에 들어가는 C 모듈 중
  테스트 전용(_testcapi 등), 서브 인터프리터/디버깅 도구, 이미 제외한 표준 라이브러리의
  확장(_asyncio, pyexpat, _elementtree), CJK 코덱(일본/중국/대만) 등을 뺍니다.
  `decimal` 은 `Lib/decimal.py` 의 순수 파이썬 폴백(`_pydecimal`)이 있어 안전하고,
  cp949(한국어)를 쓰는 `_codecs_kr` 과 `unicodedata` 는 남깁니다.
- **Kivy 내장 폰트/도구 정리** — `kivy/tools` 와 쓰지 않는 폰트(DejaVuSans, RobotoMono)를
  번들에서 제외합니다. Roboto 4종은 `kivy/core/text` 가 import 시점에 기본 폰트로
  등록하므로 반드시 남겨야 합니다(없으면 앱이 시작되지 않습니다).
  실제 UI 폰트는 서브셋한 NanumGothic 을 씁니다.
- **한글 폰트 서브셋** — `tools/subset_fonts.py` 가 UI 코드에 등장하는 글자만 남깁니다.
  전체 폰트는 `font_src/` 에 보관하고 APK 에는 넣지 않습니다(약 4MB → 0.35MB).
  문구를 바꾼 뒤에는 스크립트를 다시 실행하세요.
- **적응형 아이콘** — `tools/make_adaptive_icon.py` 로 `assets/icon_fg.png`(전경),
  `assets/icon_bg.png`(배경)를 생성합니다. Android 8.0+ 런처에서 잘리지 않고 표시됩니다.
- 아이콘/스플래시 원본은 빌드 설정에서만 쓰고 앱 런타임 자산에서는 제외합니다.

## 데이터

- 회차 데이터: 동행복권 공식 데이터 + `smok95.github.io/lotto` 미러(자동 동기화)
- 첫 실행 시 앱에 포함된 `data/draws.json`(1,246회차)으로 즉시 사용 가능, 이후 자동 업데이트
- 모든 계산은 단말에서 수행하며 개인정보를 전송하지 않습니다.
- **외부 파이썬 패키지 의존성 없음**: HTTP는 표준 라이브러리(`urllib` + `ssl`)만 사용하고,
  HTTPS 인증서는 `assets/cacert.pem`(Mozilla CA 번들)으로 검증합니다.
  (p4a 빌드에서 순수 파이썬 패키지 설치가 실패하는 문제를 제거하고 APK 용량도 줄입니다.)
- 한글 폰트: `assets/NanumGothic-Regular.ttf` / `-Bold.ttf` (OFL 라이선스, UI 글자만 서브셋)
