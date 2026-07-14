import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 음성 연락처: RAG(ChromaDB) 영속 + RAM 캐시 + 단말 주소록 이중 SoT.
# ==========================================
#
# 💡 [면접 대비 주석 - 왜 RAG인가 (사용자 결정)]
# Q. 연락처를 RAG에 넣는 건 비권장 아닌가요?
# A. "사실 데이터는 DB 정확 매칭이 이상적이지만, RAG 경로 종단 시연을 위해
#    사용자가 RAG 기반으로 전환을 결정했다. LLM 환각 위험은 metadata에서
#    번호를 직접 꺼내 제거했고, 유사도 불확실성은 이름 정규화 후보 필터로
#    방어했다. RAM 캐시와 단말 주소록은 보조 계층으로 유지한다."

from server.rag.contact_rag import get_default_contact_rag_store
from server.services.device_registry_service import get_cached_device_ids
from server.stt.contact_store import ContactStore, normalize_contact_name


class ContactService:
    """연락처 저장/조회/캐시 복구 서비스 계층(RAG 기반)."""

    @staticmethod
    def _get_store():
        return get_default_contact_rag_store()

    @staticmethod
    async def save(device_uuid: str, display_name: str, phone_number: str) -> bool:
        """RAM 캐시 + RAG(ChromaDB) 저장. RAG 저장 성공 여부를 반환한다."""
        ContactStore.save(device_uuid, display_name, phone_number)

        user_id, _ = get_cached_device_ids(device_uuid)
        if user_id is None:
            print(
                f"[ContactService] RAG 저장 스킵(단말 미등록): device_uuid={device_uuid}, "
                f"name={display_name}"
            )
            return False

        normalized_name = normalize_contact_name(display_name)
        store = ContactService._get_store()
        if store is None:
            print(
                f"[ContactService] RAG 스토어 미초기화 - RAM 캐시만 저장: "
                f"device_uuid={device_uuid}, name={display_name}"
            )
            return False

        try:
            store.save(
                user_id=user_id,
                device_uuid=device_uuid,
                display_name=display_name,
                normalized_name=normalized_name,
                phone_number=phone_number,
            )
            return True
        except Exception as e:
            print(
                f"[ContactService] RAG 저장 실패: device_uuid={device_uuid}, "
                f"name={display_name}, {e}"
            )
            return False

    @staticmethod
    async def lookup(device_uuid: str, name: str) -> str | None:
        """RAM -> RAG 순으로 이름에 해당하는 전화번호를 조회한다."""
        phone = ContactStore.lookup(device_uuid, name)
        if phone:
            return phone

        user_id, _ = get_cached_device_ids(device_uuid)
        if user_id is None:
            return None

        normalized_name = normalize_contact_name(name)
        store = ContactService._get_store()
        if store is None:
            return None

        try:
            phone = store.lookup(user_id, normalized_name)
            if phone:
                ContactStore.save(device_uuid, name, phone)
            return phone
        except Exception as e:
            print(
                f"[ContactService] RAG 조회 실패: device_uuid={device_uuid}, "
                f"name={name}, {e}"
            )
            return None

    @staticmethod
    async def hydrate_cache(device_uuid: str) -> int:
        """WS 재접속 시 RAG 연락처를 RAM 캐시로 복구한다."""
        user_id, _ = get_cached_device_ids(device_uuid)
        if user_id is None:
            return 0

        store = ContactService._get_store()
        if store is None:
            return 0

        try:
            contacts = store.list_by_user(user_id)
            for contact in contacts:
                display_name = contact.get("display_name") or ""
                phone_number = contact.get("phone_number") or ""
                if display_name and phone_number:
                    ContactStore.save(device_uuid, display_name, phone_number)
            return len(contacts)
        except Exception as e:
            print(
                f"[ContactService] RAG 캐시 복구 실패: device_uuid={device_uuid}, {e}"
            )
            return 0
