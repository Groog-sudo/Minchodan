// client/src/services/ttsPlayer.ts
import Tts from 'react-native-tts';

// TTS 엔진 초기화 설정 (Vibe)
Tts.setDefaultLanguage('ko-KR');
Tts.setDefaultRate(1.2); // 빠른 발화 (Reflex용)
Tts.setDefaultPitch(1.0);

export class TTSPlayer {
  private isPreempting = false;

  async playPreempt(alertId: string, direction: string) {
    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 시작 (45% 비중) 👨‍💻
    // [면접 대비 포인트] "기존에 재생되던 3~5초짜리 긴 안내문(Cognitive)을 
    // 어떻게 중단하고 위험 경고(Reflex)를 우선 재생(Preempt)했나요?"
    
    // 1. 현재 isPreempting 상태를 true 로 바꾸세요. (동시 호출 방지 락)
    // 2. Tts.stop() 을 호출해서 현재 안드로이드 기기에서 나오던 소리를 즉시 끊으세요.
    // 3. 방향(direction)에 따라 경고 문구를 만드세요. (예: "전방에 충돌 주의", "좌측에 계단 주의")
    //    switch (direction) 문이나 if-else를 사용하면 됩니다.
    // 4. Tts.speak(경고문구) 를 호출해서 소리를 출력하세요.
    // 5. 마지막에 isPreempting 을 false 로 돌려놓으세요.
    // =========================================================================

    

    // =========================================================================
    // 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
    // =========================================================================
  }

  async playSequential(text: string) {
    // 인지(Cognitive) 경로: 상황 설명 (Vibe 처리)
    if (this.isPreempting) return; // 선점 중이면 씹기
    Tts.setDefaultRate(1.0); // 일반 속도 복귀
    Tts.speak(text);
  }
}

export const ttsPlayer = new TTSPlayer();
