"""표준 발음법 기반 한국어 텍스트 -> IPA 음소열 변환기 (순수 표준 라이브러리).

pygoruut(goruut 바이너리)의 한국어 사전이 불완전해 흔한 음절('측', '직', '걸',
'볼', '밑' 등)을 구두점으로 오분류해 발음에서 통째로 누락시키는 결함이
2026-07-09 실측으로 확인됐다(예: '우측으로 돌아가세요' -> '우으로 돌아가세요').
Piper 모델(piper-kss-korean.onnx)은 pygoruut 음소 체계로 학습됐으므로,
이 모듈은 pygoruut이 정상 변환한 단어들에서 관측된 표기 관례(무성 파열음
어두 유지, 모음 사이 유성화, ㅔ/ㅐ -> ɛ 등)를 그대로 따르는 규칙 기반
변환기를 제공한다. tts_service._phonemize()가 pygoruut 결과에서 한글 음절
누락을 감지하면 이 변환기로 문장 전체를 대체 변환한다.

지원 음운 규칙(표준 발음법 근거):
- 연음 (제13항~제15항): 받침 + 모음 시작 음절 -> 받침이 초성으로 이동
- 비음화 (제18항): 장애음 받침 + 비음 초성 -> ㅇ/ㄴ/ㅁ으로 동화
- 유음화 (제20항): ㄴ+ㄹ / ㄹ+ㄴ -> ll
- ㅎ 처리 (제12항): 받침 ㅎ + 모음 -> 탈락, ㅎ 인접 평파열음 -> 격음화
- 구개음화 (제17항): 받침 ㄷ/ㅌ + '이' -> 지/치
- 겹받침 대표음 (제10항~제11항)
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# [파트 1] 자모 테이블 및 IPA 매핑
# ============================================================

_HANGUL_BASE = 0xAC00
_NUM_VOWELS = 21
_NUM_FINALS = 28

_ONSETS = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
_VOWELS = [
    "ㅏ",
    "ㅐ",
    "ㅑ",
    "ㅒ",
    "ㅓ",
    "ㅔ",
    "ㅕ",
    "ㅖ",
    "ㅗ",
    "ㅘ",
    "ㅙ",
    "ㅚ",
    "ㅛ",
    "ㅜ",
    "ㅝ",
    "ㅞ",
    "ㅟ",
    "ㅠ",
    "ㅡ",
    "ㅢ",
    "ㅣ",
]
_FINALS = [
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]

# 초성 IPA (무성 기본형). 유성화는 파트 3에서 문맥에 따라 적용한다.
# pygoruut 관측 관례: ㅈ는 모음 사이에서도 tɕ 유지, ㄱ/ㄷ/ㅂ만 유성화.
_ONSET_IPA = {
    "ㄱ": "k",
    "ㄲ": "k",
    "ㄴ": "n",
    "ㄷ": "t",
    "ㄸ": "t",
    "ㄹ": "ɾ",
    "ㅁ": "m",
    "ㅂ": "p",
    "ㅃ": "p",
    "ㅅ": "s",
    "ㅆ": "s",
    "ㅇ": "",
    "ㅈ": "tɕ",
    "ㅉ": "tɕ",
    "ㅊ": "tɕʰ",
    "ㅋ": "kʰ",
    "ㅌ": "tʰ",
    "ㅍ": "pʰ",
    "ㅎ": "h",
}

# 모음 사이 유성화 대응 (표준 발음에서 평파열음의 유성 변이음).
_VOICED = {"k": "g", "t": "d", "p": "b"}

_VOWEL_IPA = {
    "ㅏ": "a",
    "ㅐ": "ɛ",
    "ㅑ": "ja",
    "ㅒ": "jɛ",
    "ㅓ": "ʌ",
    "ㅔ": "ɛ",
    "ㅕ": "jʌ",
    "ㅖ": "jɛ",
    "ㅗ": "o",
    "ㅘ": "wa",
    "ㅙ": "wɛ",
    "ㅚ": "wɛ",
    "ㅛ": "jo",
    "ㅜ": "u",
    "ㅝ": "wʌ",
    "ㅞ": "wɛ",
    "ㅟ": "wi",
    "ㅠ": "ju",
    "ㅡ": "ɯ",  # noqa: RUF001 (IPA 근후설 비원순 모음, 라틴 w 아님)
    "ㅢ": "ɯi",  # noqa: RUF001
    "ㅣ": "i",
}

# 받침 대표음 7종성 (표준 발음법 제8항~제11항).
_FINAL_REPRESENTATIVE = {
    "": "",
    "ㄱ": "ㄱ",
    "ㄲ": "ㄱ",
    "ㄳ": "ㄱ",
    "ㄴ": "ㄴ",
    "ㄵ": "ㄴ",
    "ㄶ": "ㄴ",
    "ㄷ": "ㄷ",
    "ㄹ": "ㄹ",
    "ㄺ": "ㄱ",
    "ㄻ": "ㅁ",
    "ㄼ": "ㄹ",
    "ㄽ": "ㄹ",
    "ㄾ": "ㄹ",
    "ㄿ": "ㅂ",
    "ㅀ": "ㄹ",
    "ㅁ": "ㅁ",
    "ㅂ": "ㅂ",
    "ㅄ": "ㅂ",
    "ㅅ": "ㄷ",
    "ㅆ": "ㄷ",
    "ㅇ": "ㅇ",
    "ㅈ": "ㄷ",
    "ㅊ": "ㄷ",
    "ㅋ": "ㄱ",
    "ㅌ": "ㄷ",
    "ㅍ": "ㅂ",
}

# 연음 시 겹받침 분리: (남는 받침, 다음 초성으로 넘어가는 자음).
_CLUSTER_SPLIT = {
    "ㄳ": ("ㄱ", "ㅅ"),
    "ㄵ": ("ㄴ", "ㅈ"),
    "ㄶ": ("ㄴ", "ㅎ"),
    "ㄺ": ("ㄹ", "ㄱ"),
    "ㄻ": ("ㄹ", "ㅁ"),
    "ㄼ": ("ㄹ", "ㅂ"),
    "ㄽ": ("ㄹ", "ㅅ"),
    "ㄾ": ("ㄹ", "ㅌ"),
    "ㄿ": ("ㄹ", "ㅍ"),
    "ㅀ": ("ㄹ", "ㅎ"),
    "ㅄ": ("ㅂ", "ㅆ"),
}

_FINAL_IPA = {
    "": "",
    "ㄱ": "k",
    "ㄴ": "n",
    "ㄷ": "t",
    "ㄹ": "l",
    "ㅁ": "m",
    "ㅂ": "p",
    "ㅇ": "ŋ",
}

# 격음화: 평음 + ㅎ 또는 ㅎ + 평음 -> 격음 (표준 발음법 제12항).
_ASPIRATE = {"ㄱ": "ㅋ", "ㄷ": "ㅌ", "ㅂ": "ㅍ", "ㅈ": "ㅊ"}

_NASALIZE = {"ㄱ": "ㅇ", "ㄷ": "ㄴ", "ㅂ": "ㅁ"}


def _decompose(char: str) -> tuple[str, str, str] | None:
    """한글 완성형 음절을 (초성, 중성, 종성) 자모로 분해한다. 한글이 아니면 None."""
    code = ord(char) - _HANGUL_BASE
    if not 0 <= code < len(_ONSETS) * _NUM_VOWELS * _NUM_FINALS:
        return None
    onset = _ONSETS[code // (_NUM_VOWELS * _NUM_FINALS)]
    vowel = _VOWELS[(code % (_NUM_VOWELS * _NUM_FINALS)) // _NUM_FINALS]
    final = _FINALS[code % _NUM_FINALS]
    return onset, vowel, final


# ============================================================
# [파트 2] 음운 변동 적용 (자모 수준)
# ============================================================


def _apply_phonology(syllables: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """단어 내 인접 음절 간 표준 발음법 규칙을 적용한다."""
    result = [list(s) for s in syllables]

    for i in range(len(result) - 1):
        onset_next = result[i + 1][0]
        vowel_next = result[i + 1][1]
        final = result[i][2]
        if not final:
            continue

        # 구개음화 (제17항): ㄷ/ㅌ 받침 + 조사·접미사 '이' -> 지/치
        if onset_next == "ㅇ" and vowel_next == "ㅣ" and final in ("ㄷ", "ㅌ"):
            result[i][2] = ""
            result[i + 1][0] = "ㅈ" if final == "ㄷ" else "ㅊ"
            continue

        # 연음 (제13항~제14항): 받침 + ㅇ 초성 -> 받침 이동
        if onset_next == "ㅇ":
            if final == "ㅎ":
                result[i][2] = ""  # ㅎ 탈락 (제12항)
            elif final in _CLUSTER_SPLIT:
                remain, move = _CLUSTER_SPLIT[final]
                result[i][2] = remain
                result[i + 1][0] = "ㅆ" if move == "ㅆ" else move
            elif final == "ㅇ":
                pass  # ㅇ 받침은 이동하지 않음 (종성 ŋ 유지)
            else:
                result[i][2] = ""
                result[i + 1][0] = final
            continue

        # 격음화 (제12항): ㅎ 받침 + 평음 / 평파열음 받침 + ㅎ 초성
        rep = _FINAL_REPRESENTATIVE[final]
        if final in ("ㅎ", "ㄶ", "ㅀ") and onset_next in _ASPIRATE:
            result[i][2] = "" if final == "ㅎ" else ("ㄴ" if final == "ㄶ" else "ㄹ")
            result[i + 1][0] = _ASPIRATE[onset_next]
            continue
        if onset_next == "ㅎ" and rep in ("ㄱ", "ㄷ", "ㅂ"):
            result[i][2] = ""
            result[i + 1][0] = _ASPIRATE[{"ㄱ": "ㄱ", "ㄷ": "ㄷ", "ㅂ": "ㅂ"}[rep]]
            continue

        # 비음화 (제18항): 장애음 받침 + ㄴ/ㅁ
        if onset_next in ("ㄴ", "ㅁ") and rep in _NASALIZE:
            result[i][2] = _NASALIZE[rep]
            continue

        # 유음화 (제20항): ㄴ+ㄹ, ㄹ+ㄴ -> ㄹㄹ
        if rep == "ㄴ" and onset_next == "ㄹ":
            result[i][2] = "ㄹ"
            continue
        if rep == "ㄹ" and onset_next == "ㄴ":
            result[i][2] = "ㄹ"
            result[i + 1][0] = "ㄹ"
            continue

        # 그 외: 대표음으로 중화 (제8항~제11항)
        result[i][2] = rep

    # 어말 받침도 대표음으로 중화
    if result:
        result[-1][2] = _FINAL_REPRESENTATIVE[result[-1][2]]

    return [(s[0], s[1], s[2]) for s in result]


# ============================================================
# [파트 3] IPA 렌더링 (유성화 및 ㄹ 변이음 포함)
# ============================================================


def _render_ipa(syllables: list[tuple[str, str, str]]) -> str:
    """음운 변동이 끝난 자모열을 IPA 문자열로 렌더링한다."""
    parts: list[str] = []
    prev_ended_vowel = False  # 직전 음절이 모음으로 끝났는지 (유성화 판단)
    prev_final_l = False

    for onset, vowel, final in syllables:
        onset_ipa = _ONSET_IPA[onset]

        # 모음 사이 평파열음 유성화 (pygoruut 관측 관례: 모음 사이 및 ɾ 뒤)
        if onset_ipa in _VOICED and prev_ended_vowel:
            onset_ipa = _VOICED[onset_ipa]

        # ㄹ: ㄹㄹ 연쇄는 ll, 그 외 초성은 탄설음 ɾ
        if onset == "ㄹ" and prev_final_l:
            onset_ipa = "l"

        parts.append(onset_ipa + _VOWEL_IPA[vowel] + _FINAL_IPA[_FINAL_REPRESENTATIVE[final]])
        rep_final = _FINAL_REPRESENTATIVE[final]
        prev_ended_vowel = rep_final == ""
        prev_final_l = rep_final == "ㄹ"

    return "".join(parts)


# ============================================================
# [파트 4] 공개 API
# ============================================================


def phonemize_korean(text: str) -> str:
    """한국어 문장을 IPA 음소열로 변환한다. 공백은 유지하고 비한글 문자는 버린다.

    반환 문자열은 piper-kss-korean 모델의 phoneme_id_map 부분집합만 사용하며,
    tts_service._phonemize()의 phoneme_id_map 필터를 통과한다.
    """
    if not text:
        return ""

    words_out: list[str] = []
    for word in text.split():
        syllables: list[tuple[str, str, str]] = []
        for ch in word:
            jamo = _decompose(ch)
            if jamo is not None:
                syllables.append(jamo)
        if not syllables:
            continue
        words_out.append(_render_ipa(_apply_phonology(syllables)))

    return " ".join(words_out)
