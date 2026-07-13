import { useState } from "react";
import { useMembers } from "../api/useMembers";
import type { AppUserRow } from "../types/monitor";

const PAGE_SIZE = 10;

/** 회원이 익명 자동등록 상태인지, 정식 등록됐는지 보여주는 배지. */
function MemberStatusPill({ isAnonymous }: { isAnonymous: boolean }) {
  return isAnonymous ? (
    <span className="member-status-pill member-status-anon">익명 자동등록</span>
  ) : (
    <span className="member-status-pill member-status-real">정식 회원</span>
  );
}

export function MembersPage({ token }: { token: string }) {
  const [page, setPage] = useState(0);
  const { rows, totalCount, loading, error, registerMember, refresh } = useMembers(
    token,
    page,
    PAGE_SIZE,
  );

  const [deviceUuid, setDeviceUuid] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [disabilitySeverity, setDisabilitySeverity] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [guardianPhone, setGuardianPhone] = useState("");
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formMessage, setFormMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  // 익명 자동등록 행의 "회원 정보 입력" 버튼 클릭 시 폼에 device_uuid를 채워두고
  // 관리자가 이름/전화번호/장애정도만 입력하면 바로 전환되게 한다.
  const resetForm = () => {
    setDeviceUuid("");
    setName("");
    setPhone("");
    setDisabilitySeverity("");
    setBirthDate("");
    setGuardianPhone("");
    setAddress("");
  };

  const prefillFromAnonymous = (row: AppUserRow) => {
    resetForm();
    setDeviceUuid(row.devices[0]?.device_uuid ?? "");
    setFormMessage(null);
    document.getElementById("member-register-form")?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!deviceUuid || !name || !phone || !disabilitySeverity) {
      setFormMessage({ ok: false, text: "기기 식별자/이름/전화번호/장애정도는 필수입니다." });
      return;
    }
    setSubmitting(true);
    const result = await registerMember({
      device_uuid: deviceUuid,
      name,
      phone,
      disability_severity: disabilitySeverity,
      birth_date: birthDate || undefined,
      guardian_phone: guardianPhone || undefined,
      address: address || undefined,
    });
    setSubmitting(false);
    setFormMessage({ ok: result.ok, text: result.message });
    if (result.ok) {
      resetForm();
      setPage(0);
    }
  };

  return (
    <>
      <section id="member-register-form" className="panel panel-member-form">
        <div className="panel-header">
          <h2>회원 등록</h2>
          <span className="panel-kicker">시각장애인 회원 등록/전환</span>
        </div>
        <p className="member-form-hint">
          아래 목록에서 "익명 자동등록" 상태인 기기의 "회원 정보 입력" 버튼을 누르면 기기
          식별자(device_uuid)가 자동으로 채워집니다. 이미 등록된 device_uuid를 입력하면 그
          회원 정보가 갱신됩니다(신규 회원이 중복 생성되지 않음).
        </p>
        <form className="member-form" onSubmit={handleSubmit}>
          <label>
            기기 식별자(device_uuid)
            <input
              type="text"
              value={deviceUuid}
              onChange={(e) => setDeviceUuid(e.target.value)}
              placeholder="예: dev-001"
              required
            />
          </label>
          <label>
            이름
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="홍길동"
              required
            />
          </label>
          <label>
            전화번호
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="010-0000-0000"
              required
            />
          </label>
          <label>
            장애 정도
            <input
              type="text"
              value={disabilitySeverity}
              onChange={(e) => setDisabilitySeverity(e.target.value)}
              placeholder="예: 시각장애 1급"
              required
            />
          </label>
          <label>
            생년월일 (선택)
            <input
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
            />
          </label>
          <label>
            보호자 연락처 (선택)
            <input
              type="text"
              value={guardianPhone}
              onChange={(e) => setGuardianPhone(e.target.value)}
              placeholder="010-0000-0000"
            />
          </label>
          <label>
            주소 (선택)
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="서울시 강남구 ..."
            />
          </label>
          <button type="submit" className="refresh-btn" disabled={submitting}>
            {submitting ? "등록 중..." : "등록"}
          </button>
        </form>
        {formMessage && (
          <p className={formMessage.ok ? "member-form-message-ok" : "member-form-message-error"}>
            {formMessage.text}
          </p>
        )}
      </section>

      <section className="panel panel-table">
        <div className="panel-header">
          <h2>등록 회원 목록</h2>
          <div className="panel-header-actions">
            <button
              type="button"
              className="refresh-btn"
              onClick={() => refresh()}
              disabled={loading}
            >
              {loading ? "새로고침 중..." : "새로고침"}
            </button>
            <span className="panel-kicker">전체 {totalCount}명</span>
          </div>
        </div>

        {error && <p className="member-form-message-error">{error}</p>}

        {rows.length === 0 ? (
          <p className="empty-text">등록된 회원이 없습니다.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>이름</th>
                  <th>전화번호</th>
                  <th>장애정도</th>
                  <th>생년월일</th>
                  <th>보호자 연락처</th>
                  <th>주소</th>
                  <th>기기(device_uuid)</th>
                  <th>상태</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.user_id}>
                    <td>{row.is_anonymous ? "-" : row.name}</td>
                    <td>{row.is_anonymous ? "-" : row.phone}</td>
                    <td>{row.is_anonymous ? "-" : row.disability_severity}</td>
                    <td>{row.birth_date ?? "-"}</td>
                    <td>{row.guardian_phone ?? "-"}</td>
                    <td>{row.address ?? "-"}</td>
                    <td>
                      {row.devices.map((d) => (
                        <div key={d.device_id}>
                          {d.device_uuid} ({d.platform})
                        </div>
                      ))}
                    </td>
                    <td>
                      <MemberStatusPill isAnonymous={row.is_anonymous} />
                    </td>
                    <td>
                      {row.is_anonymous && (
                        <button
                          type="button"
                          className="page-btn"
                          onClick={() => prefillFromAnonymous(row)}
                        >
                          회원 정보 입력
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <nav className="log-pagination" aria-label="회원 목록 페이지 이동">
            <button
              type="button"
              className="page-btn"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              이전
            </button>
            <span className="page-indicator">
              {page + 1} / {totalPages} 페이지 · 전체 {totalCount}명
            </span>
            <button
              type="button"
              className="page-btn"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              다음
            </button>
          </nav>
        )}
      </section>
    </>
  );
}
