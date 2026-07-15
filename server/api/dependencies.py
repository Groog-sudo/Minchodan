import logging

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# JWT 토큰을 추출하고 검증하는 중앙 의존성(문지기) 계층입니다.
# ==========================================
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from server.db.security import decode_access_token

logger = logging.getLogger(__name__)

# FastAPI 표준 OAuth2 토큰 추출기 (이걸 써야 Swagger UI에 자물쇠 버튼이 생김)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login", auto_error=False)


async def get_current_admin(
    token_query: str | None = Query(None, alias="token"),
    token_header: str | None = Depends(oauth2_scheme),
) -> str:
    """
    들어온 요청에서 JWT를 추출하고 검증하여, 유효한 관리자 사번(employee_no)을 반환합니다.
    """

    # 💡 [면접 대비 주석 - SSE 토큰 꼼수(Workaround)]
    # Q. 왜 토큰을 헤더(token_header)랑 쿼리(token_query) 두 곳에서 굳이 다 찾나요?
    # A. "프론트엔드 관제 콘솔에서 사용하는 EventSource(SSE) API는 브라우저 보안 스펙상
    #    'Authorization' 커스텀 헤더를 마음대로 추가할 수 없습니다.
    #    따라서 SSE 스트리밍 연결 시에는 부득이하게 URL 쿼리(?token=...)로 토큰을 받고,
    #    그 외 일반 REST API 요청들은 정석대로 헤더에서 받게끔 유연하게 설계했습니다."

    token = token_query or token_header

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 없습니다 (SEE는 ? token=...파라미터 필요)",
        )

    try:
        # security.py에 짜둔 함수로 토큰 까보기
        payload = decode_access_token(token)
        employee_no = payload.get("sub")  # sub(Subject) 필드에 사번 들어있음
        if employee_no is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 사용자 식별(sub)가 없습니다.",
            )

        return employee_no

    except InvalidTokenError:
        logger.warning(f"잘못되거나 만료된 토큰 접근 시도: {token[:10]}....")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었거나 유효하지 않습니다.",
        ) from None
