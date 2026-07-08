export function OperatorLiveMap() {
  return (
    <section className="panel" style={{ minHeight: '400px', padding:0, overflow: 'hidden'}}>
      {/* 💡 [면접 대비 주석 - 마이크로서비스 연동] 
          네이비게이션은 8001번 독립 서버에서 구동됩니다
          콘솔은 무거운 지도 라이브러리를 직접 들고 있지 않고. iframe embed 옵션으로 화면만 가져와 랜더링 부하를 없앴습니다.
      */}
      <iframe 
        src="http://localhost:8001/?embed=true"
        title="스마트 가이드독 실시간 보행 관제 지도"
        width="100%"
        height="100%"
        style={{ border : 'none', display : 'block'}}
        >
      </iframe>

    </section>
  );

}