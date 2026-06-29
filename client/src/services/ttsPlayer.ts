import Tts from 'react-native-tts';

export type MessageHintId =
  | 'OBSTACLE'
  | 'STAIR_DOWN'
  | 'ROAD'
  | 'RED_LIGHT'
  | 'CURB'
  | 'STOP';

export type MessageHintType = 'REFLEX' | 'COGNITIVE';

export interface MessageHint {
  id: MessageHintId;
  type: MessageHintType;
  text: string;
}

class TtsPlayer {
  private cognitiveQueue: Promise<void> = Promise.resolve();

  async speak(hint: MessageHint): Promise<void> {
    const text = hint.text.trim();
    if (!text) {
      return;
    }

    if (hint.type === 'REFLEX') {
      await this.stop();
      // TODO(prod reflex): playClip(hint.id) 로 교체, 실패 시 Tts.speak(hint.text) 폴백
      Tts.speak(text);
      return;
    }

    this.cognitiveQueue = this.cognitiveQueue
      .catch(() => undefined)
      .then(async () => {
        Tts.speak(text);
      });
    await this.cognitiveQueue;
  }

  async stop(): Promise<void> {
    await Tts.stop();
  }
}

export const ttsPlayer = new TtsPlayer();

export async function speakMessageHint(hint: MessageHint): Promise<void> {
  await ttsPlayer.speak(hint);
}
