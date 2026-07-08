import { useState } from "react";
import "./Login.css";


// ==========================================
// 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
// 백엔드의 OAuth2 로그인 표준(x-www-form-urlencoded)에 맞춰
// JWT 토큰을 발급받아오는 프론트엔드 폼 컴포넌트입니다.
// ==========================================

export function Login({ onLogin } : { onLogin: (token: string) => void}) {
  const [employeeNo, setEmployeeNo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      // 💡 [면접 대비 주석 - OAuth2 폼 전송]
      // Q. 왜 굳이 복잡하게 URLSearchParams를 써서 데이터를 보내나요? JSON 쓰면 안 되나요?
      // # A. "백엔드가 FastAPI의 내장 'OAuth2PasswordRequestForm'을 사용하기 때문입니다.
      // #    이 표준 스펙은 JSON 대신 'x-www-form-urlencoded' 타입으로 데이터를 받도록
      // #    강제하기 때문에, 프론트에서도 그 규칙에 맞춰 폼 데이터를 전송하는 것입니다."

      const formData = new URLSearchParams();
      formData.append("username", employeeNo);
      formData.append("password", password);

      const response = await fetch("http://localhost:8000/api/v1/admin/login", {
        method: "POST",
        headers: {
          "Content-Type" : "application/x-www-form-urlencoded",
        },
        body: formData.toString()      
      });

      if(!response.ok){
        throw new Error("사번 또는 비밀번호가 틀렸습니다.")
      }

      const data = await response.json();
      // 발급받은 JWT 토큰(access_token)을 부모(App.tsx)에게 넘겨줌
      onLogin(data.access_token);
    }catch (err: any){
      setError(err.message);
    }
  };

  return (
    <div className="login-container">
      <form onSubmit={handleLogin} className="login-form">
        <h2 className="login-title">Minchodan Console</h2>
        <p className="login-subtitle">관리자 로그인이 필요합니다.</p>
        
        <input 
          type="text" 
          placeholder="사번 (Employee No)" 
          value={employeeNo} 
          onChange={e => setEmployeeNo(e.target.value)}
          className="login-input"
        />
        <input 
          type="password" 
          placeholder="비밀번호" 
          value={password} 
          onChange={e => setPassword(e.target.value)}
          className="login-input"
        />
        
        {error && <div className="login-error">{error}</div>}
        
        <button type="submit" className="login-button">
          로그인 (JWT 발급)
        </button>
      </form>
    </div>
  );
}