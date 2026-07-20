import { useEffect, useMemo, useRef, useState } from "react";
import type { RiskEvent } from "../types/monitor";

const PAGE_SIZE = 10;
const PAGE_BUTTON_WINDOW = 10;

function formatTs(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function RiskLevelBadge({ level }: { level: RiskEvent["risk_level"] }) {
  return <span className={`risk-pill risk-${level}`}>{level}</span>;
}

export function RiskEventLog({ events }: { events: RiskEvent[] }) {
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isPageSearchOpen, setIsPageSearchOpen] = useState(false);
  const [pageSearchInput, setPageSearchInput] = useState("");
  const pageSearchRef = useRef<HTMLDivElement | null>(null);

  const sortedEvents = useMemo(
    () =>
      [...events].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()),
    [events],
  );

  const totalCount = sortedEvents.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const disablePaginationControls = totalCount <= 11;

  const pageWindowStart = Math.floor(safePage / PAGE_BUTTON_WINDOW) * PAGE_BUTTON_WINDOW;
  const pageWindowEnd = Math.min(totalPages, pageWindowStart + PAGE_BUTTON_WINDOW);
  const visiblePages = Array.from(
    { length: pageWindowEnd - pageWindowStart },
    (_, index) => pageWindowStart + index,
  );

  const pageRows = useMemo(() => {
    const start = safePage * PAGE_SIZE;
    return sortedEvents.slice(start, start + PAGE_SIZE);
  }, [sortedEvents, safePage]);

  const selected = pageRows.find((row) => row.id === selectedId) ?? null;

  useEffect(() => {
    if (page !== safePage) {
      setPage(safePage);
    }
  }, [page, safePage]);

  useEffect(() => {
    if (selectedId !== null && !pageRows.some((row) => row.id === selectedId)) {
      setSelectedId(null);
    }
  }, [pageRows, selectedId]);

  useEffect(() => {
    if (!isPageSearchOpen) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (!pageSearchRef.current) return;
      if (!pageSearchRef.current.contains(event.target as Node)) {
        setIsPageSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isPageSearchOpen]);

  const jumpToPage = () => {
    const parsed = Number.parseInt(pageSearchInput.trim(), 10);
    if (Number.isNaN(parsed)) return;
    const clampedPage = Math.min(totalPages, Math.max(1, parsed));
    setPage(clampedPage - 1);
    setPageSearchInput("");
    setIsPageSearchOpen(false);
  };

  return (
    <section className="panel panel-table">
      <div className="panel-header">
        <h2>RiskEventLog</h2>
        <div className="panel-header-actions">
          <span className="panel-kicker">
            위험 로그 · {totalCount}건
          </span>
        </div>
      </div>

      {pageRows.length === 0 ? (
        <p className="empty-text">아직 위험 이벤트가 없습니다.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>위험도</th>
                <th>객체</th>
                <th>신뢰도</th>
                <th>방향</th>
                <th>안내문</th>
                <th>이벤트 ID</th>
                <th>시각</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((event) => (
                <tr
                  key={event.id}
                  className={event.id === selectedId ? "row-selected" : undefined}
                  tabIndex={0}
                  onClick={() =>
                    setSelectedId(event.id === selectedId ? null : event.id)
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelectedId(event.id === selectedId ? null : event.id);
                    }
                  }}
                >
                  <td>
                    <RiskLevelBadge level={event.risk_level} />
                  </td>
                  <td>{event.class_name}</td>
                  <td>
                    {event.confidence !== undefined
                      ? `${(event.confidence * 100).toFixed(1)}%`
                      : "-"}
                  </td>
                  <td>{event.direction ?? "-"}</td>
                  <td className="tts-text-cell">{event.guidance_text ?? "-"}</td>
                  <td>{event.event_id}</td>
                  <td>{formatTs(event.ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <nav className="log-pagination" aria-label="위험 로그 페이지 이동">
        <button
          type="button"
          className="page-btn"
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={disablePaginationControls || safePage === 0}
          aria-label="이전 페이지"
        >
          ←
        </button>

        <div className="page-number-strip" aria-label="페이지 번호 목록">
          {visiblePages.map((pageIndex) => (
            <button
              key={pageIndex}
              type="button"
              className={`page-btn ${safePage === pageIndex ? "page-btn-active" : ""}`}
              onClick={() => setPage(pageIndex)}
              disabled={disablePaginationControls}
            >
              {pageIndex + 1}
            </button>
          ))}

          {pageWindowEnd < totalPages && (
            <>
              <div className="page-search-anchor" ref={pageSearchRef}>
                <button
                  type="button"
                  className={`page-btn page-jump-btn ${isPageSearchOpen ? "page-btn-active" : ""}`}
                  onClick={() => setIsPageSearchOpen((open) => !open)}
                  disabled={disablePaginationControls}
                  aria-label="페이지 번호 검색"
                >
                  ...
                </button>

                {isPageSearchOpen && (
                  <div className="page-search-popover">
                    <label className="page-search-label" htmlFor="risk-page-search-input">
                      페이지 번호
                    </label>
                    <div className="page-search-row">
                      <input
                        id="risk-page-search-input"
                        type="number"
                        className="page-search-input"
                        min={1}
                        max={totalPages}
                        placeholder={`1-${totalPages}`}
                        value={pageSearchInput}
                        onChange={(event) => setPageSearchInput(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            jumpToPage();
                          }
                        }}
                      />
                      <button type="button" className="page-btn" onClick={jumpToPage}>
                        이동
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <button
                type="button"
                className={`page-btn ${safePage === totalPages - 1 ? "page-btn-active" : ""}`}
                onClick={() => setPage(totalPages - 1)}
                disabled={disablePaginationControls}
              >
                {totalPages}
              </button>
            </>
          )}
        </div>

        <button
          type="button"
          className="page-btn"
          onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
          disabled={disablePaginationControls || safePage >= totalPages - 1}
          aria-label="다음 페이지"
        >
          →
        </button>
      </nav>

      {selected && (
        <div className="frame-detail">
          <div className="frame-detail-body">
            <div className="frame-detail-header">
              <div className="frame-detail-headline">
                <strong>{selected.event_id}</strong>
                <RiskLevelBadge level={selected.risk_level} />
              </div>

              <div className="frame-detail-grid">
                <div className="frame-detail-item">
                  <span className="frame-detail-label">시각</span>
                  <span className="frame-detail-value">{formatTs(selected.ts)}</span>
                </div>
                <div className="frame-detail-item">
                  <span className="frame-detail-label">객체</span>
                  <span className="frame-detail-value">{selected.class_name}</span>
                </div>
                <div className="frame-detail-item">
                  <span className="frame-detail-label">신뢰도</span>
                  <span className="frame-detail-value">
                    {selected.confidence !== undefined
                      ? `${(selected.confidence * 100).toFixed(1)}%`
                      : "-"}
                  </span>
                </div>
                <div className="frame-detail-item">
                  <span className="frame-detail-label">방향</span>
                  <span className="frame-detail-value">{selected.direction ?? "-"}</span>
                </div>
                <div className="frame-detail-item frame-detail-item-full">
                  <span className="frame-detail-label">안내문</span>
                  <span className="frame-detail-value">{selected.guidance_text ?? "-"}</span>
                </div>
                <div className="frame-detail-item frame-detail-item-full">
                  <span className="frame-detail-label">이벤트 ID</span>
                  <span className="frame-detail-value">{selected.event_id}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
