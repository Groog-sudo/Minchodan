import re
import sys
from typing import ClassVar

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 음성 명령으로 연락처를 저장하고 이름으로 전화를 거는 편의기능입니다.
# ==========================================
#
# 💡 [면접 대비 주석 - 왜 DB가 아니라 메모리 dict인가]
# Q. AppUser 테이블도 있는데 왜 여기는 DB를 안 쓰고 dict에 저장합니까?
# A. "이건 사용자가 그 자리에서 즉흥적으로 등록하는 임의 연락처(예: 엄마, 택시기사)라
#    별도 Contact 테이블/마이그레이션이 필요합니다. 데모 시연 범위는 '같은 세션에서
#    저장 -> 호출'만 검증하면 되므로 프로세스 메모리로 대체했고, 서버 재시작 시
#    사라지는 게 알려진 한계입니다. 실서비스로 가면 MariaDB에 Contact 테이블을 추가해
#    Router -> Service -> Repository 3계층(course_codebase_guide.md 17.1)으로
#    옮기면 됩니다." 참고로 보호자 긴급전화(stt_to_llm_bridge.py의
#    _handle_emergency_call)는 이것과 달리 AppUser.guardian_phone 실제 DB 컬럼을
#    조회하는 진짜 구현이다 - 두 기능을 대비해서 설명하면 좋다.

PHONE_NUMBER_PATTERN = re.compile(r"01[0-9][-\s]?\d{3,4}[-\s]?\d{4}")

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
    if not match:
        return None
    digits = re.sub(r"[-\s]", "", match.group(0))
    phone = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    name = _trim_name(text[: match.start()])
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
    """[TH HARDCODE] device_id별 연락처를 프로세스 메모리에 보관하는 데모용 저장소.

    멀티 프로세스로 스케일아웃하면 인스턴스마다 저장 내용이 달라지는 것도 이
    데모 범위에서 감수한 한계다(영속화 시 Redis 또는 MariaDB Contact 테이블로 교체).
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
