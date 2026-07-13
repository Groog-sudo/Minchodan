import re
import sys
from typing import ClassVar

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 음성 명령 연락처: 서버는 파싱/세션 캐시, 영속화는 Android 주소록(ContactsBridge).
# ==========================================
#
# 💡 [면접 대비 주석 - 왜 서버 DB가 아니라 단말 주소록 + RAM 캐시인가]
# Q. AppUser 테이블도 있는데 왜 Contact를 MariaDB에 안 만듭니까?
# A. "사용자가 체감하는 '저장' 위치는 폰 연락처 앱이다. 그래서 영속 SoT(Source of
#    Truth)는 Android ContactsContract(WRITE_CONTACTS)로 두고, 서버 ContactStore는
#    같은 세션 안에서 빠른 이름→번호 조회용 RAM 캐시만 맡는다. 서버 재시작으로
#    RAM이 비어도 dial_action.device_lookup=True로 단말이 주소록을 다시 찾아
#    건다. 보호자 긴급전화(_handle_emergency_call)는 이와 달리 AppUser.guardian_phone
#    실제 DB를 쓰는 안전 기능이다 - '데이터 성격에 따라 영속화 계층을 다르게 골랐다'
#    는 설계 판단으로 대비 설명하면 좋다."

PHONE_NUMBER_PATTERN = re.compile(r"01[0-9][-\s]?\d{3,4}[-\s]?\d{4}")

# [TH HARDCODE - 2026-07-13 실기기 실측 추가]
# 문제: "엄마 번호는 010-1234-5678 저장해줘"라고 말했는데도 연락처 저장이 안 되고
# 일반 대화(오케스트레이션)로 새는 현상을 실기기로 확인했다. 원인은 Whisper가
# 전화번호를 아라비아 숫자가 아니라 "공일공일이삼사오육칠팔"처럼 한글 숫자로
# 전사하는 경우가 있어 PHONE_NUMBER_PATTERN(아라비아 숫자 전제)이 매칭에 실패하기
# 때문이다. 아래 한글 숫자 -> 아라비아 숫자 변환은 그 폴백이다.
#
# 💡 [면접 대비 주석 - 왜 정규식을 고치지 않고 폴백을 별도로 뒀나]
# Q. 그냥 PHONE_NUMBER_PATTERN에 한글 숫자도 매칭하게 합치면 안 되나요?
# A. "일/이/오" 같은 한글 숫자 문자는 그 자체로 흔한 한국어 단어/조사이기도 해서
#    (예: "일하다", "오늘"), 짧은 매칭을 허용하면 일반 문장에서 오탐 저장이
#    발생할 위험이 있다. 그래서 최소 8~11자 연속된 한글 숫자 문자 뭉치만 후보로
#    보고, 변환 후 자릿수(11자리 + '01' 시작)까지 검증해 오탐 가능성을 최소화했다.
#    실패하면 그냥 실패(재입력 유도)하는 기존 원칙(PHONE_NUMBER_PATTERN 주석 참조)과
#    동일한 설계다.
_KOREAN_DIGIT_MAP: dict[str, str] = {
    "공": "0",
    "영": "0",
    "일": "1",
    "이": "2",
    "삼": "3",
    "사": "4",
    "오": "5",
    "육": "6",
    "륙": "6",
    "칠": "7",
    "팔": "8",
    "구": "9",
}
_KOREAN_DIGIT_CHARS = "".join(_KOREAN_DIGIT_MAP.keys())
# 한글 숫자 문자가 (구분자 포함) 9~12자 연속으로 이어진 구간만 전화번호 후보로 본다.
_KOREAN_PHONE_RUN_PATTERN = re.compile(
    rf"[{_KOREAN_DIGIT_CHARS}](?:[-\s]?[{_KOREAN_DIGIT_CHARS}]){{8,11}}"
)


def _find_korean_spoken_phone(text: str) -> tuple[str, int] | None:
    """한글 숫자로 전사된 전화번호 구간을 찾아 (아라비아 숫자 11자리, 시작 위치)로 변환한다.

    "010"으로 시작하는 11자리로 변환 가능한 첫 매칭만 채택하고, 조건을 만족하지
    못하면 None을 반환해 호출측이 저장을 포기(재입력 유도)하게 한다.
    """
    for match in _KOREAN_PHONE_RUN_PATTERN.finditer(text):
        digits = "".join(_KOREAN_DIGIT_MAP.get(ch, "") for ch in match.group(0))
        if len(digits) == 11 and digits.startswith("01"):
            return digits, match.start()
    return None


# [TH HARDCODE] 형태소 분석기(KoNLPy 등) 없이 문자열 트리밍만으로 이름 후보를
# 정리하는 휴리스틱이다. 정확한 개체명 인식(NER)이 아니라 데모 발화 패턴만 커버한다.
_NAME_TRIM_SUFFIXES = ["번호는", "번호를", "번호", "한테", "에게", "님", "은", "는", "을", "를"]


def _trim_name(raw: str) -> str:
    """조사/어미를 순차 제거해 이름 후보 문자열을 정리한다."""
    name = raw.strip()
    changed = True
    while changed:
        changed = False
        for suffix in _NAME_TRIM_SUFFIXES:
            if name.endswith(suffix) and len(name) > len(suffix):
                name = name[: -len(suffix)].strip()
                changed = True
    return name


def extract_save_command(text: str) -> tuple[str, str] | None:
    """"<이름> 번호(는) <전화번호> 저장해줘" 형태 발화에서 이름/전화번호를 추출한다.

    [TH HARDCODE] 정규식 + 문자열 트리밍 기반 휴리스틱이다.
    💡 [면접 대비 주석 - 왜 LLM 개체명 추출을 안 썼나]
    Q. gemma4:e4b가 이미 붙어있는데 이름/번호 추출도 LLM한테 시키면 되지 않나요?
    A. "이 기능은 반사 경로처럼 실시간성이 생명은 아니지만, LLM 환각으로 엉뚱한
       번호가 저장되면(예: 010이 아닌 자리수를 만들어냄) 안전 문제로 번질 수
       있습니다. 정규식은 실패하면 그냥 실패(재입력 유도)해서 틀린 값을 저장할
       위험이 없어 규칙 기반을 선택했습니다."
    """
    match = PHONE_NUMBER_PATTERN.search(text)
    if match:
        digits = re.sub(r"[-\s]", "", match.group(0))
        match_start = match.start()
    else:
        # [TH HARDCODE - 2026-07-13] 아라비아 숫자 매칭 실패 시 한글 숫자 전사
        # 폴백을 시도한다(_find_korean_spoken_phone 주석 참조).
        korean_result = _find_korean_spoken_phone(text)
        if korean_result is None:
            return None
        digits, match_start = korean_result

    phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    name = _trim_name(text[:match_start])
    if not name:
        return None
    return name, phone


def extract_call_target(text: str) -> str | None:
    """"<이름>한테 전화 걸어줘" 형태 발화에서 호출 대상 이름을 추출한다."""
    for marker in ("한테", "에게"):
        idx = text.find(marker)
        if idx > 0:
            return _trim_name(text[:idx])
    return None


class ContactStore:
    """[TH HARDCODE] device_id별 연락처 세션 캐시(프로세스 메모리).

    영속 SoT는 단말 Android 주소록(contact_save / device_lookup)이다.
    여기 dict는 같은 서버 세션에서 이름→번호 조회를 빠르게 하기 위한 캐시이며,
    재시작으로 비어도 단말이 주소록에서 다시 찾는다.
    """

    _contacts: ClassVar[dict[str, dict[str, str]]] = {}

    @classmethod
    def save(cls, device_id: str, name: str, phone_number: str) -> None:
        cls._contacts.setdefault(device_id, {})[name] = phone_number

    @classmethod
    def lookup(cls, device_id: str, name: str) -> str | None:
        device_contacts = cls._contacts.get(device_id, {})
        if name in device_contacts:
            return device_contacts[name]
        # [TH HARDCODE] 완전 일치 우선, 실패 시 부분 일치 폴백(조사 트리밍 누락 대비).
        for saved_name, phone in device_contacts.items():
            if saved_name in name or name in saved_name:
                return phone
        return None
