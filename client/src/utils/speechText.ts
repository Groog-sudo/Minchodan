/** TTS 입력에서 하이픈 전화번호만 자릿수 단위 한국어 발화로 변환한다. */

const SPOKEN_DIGITS: Record<string, string> = {
  "0": "공",
  "1": "일",
  "2": "이",
  "3": "삼",
  "4": "사",
  "5": "오",
  "6": "육",
  "7": "칠",
  "8": "팔",
  "9": "구",
};

function speakDigitGroup(group: string): string {
  return [...group].map((digit) => SPOKEN_DIGITS[digit] ?? digit).join(" ");
}

export function normalizeTextForSpeech(text: string): string {
  if (!text) return "";
  return text.replace(
    /(^|[^\d])(?:(0\d{1,2})[-\s](\d{3,4})[-\s](\d{4})|(1[568]\d{2})[-\s](\d{4}))(?!\d)/g,
    (
      _match,
      prefix: string,
      area: string | undefined,
      middle: string | undefined,
      last: string | undefined,
      servicePrefix: string | undefined,
      serviceLast: string | undefined,
    ) => {
      const groups = area
        ? [area, middle, last]
        : [servicePrefix, serviceLast];
      return `${prefix}${groups.filter(Boolean).map((group) => speakDigitGroup(group!)).join(", ")} `;
    },
  );
}
