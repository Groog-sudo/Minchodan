/**
 * Android 주소록(ContactsContract) 브릿지.
 * iOS는 공개 Contacts 쓰기 권한이 달라 이번 범위에서 미지원(Android 전용).
 *
 * ==========================================
 * TH HARDCODE AREA (면접/발표 핵심 방어 영역)
 * 음성 연락처 저장/조회의 단말 측 영속화 계층.
 * ==========================================
 *
 * [면접 대비 주석 - 왜 서버 DB가 아니라 폰 주소록인가]
 * Q. ContactStore(서버 RAM)만으로 충분하지 않나요?
 * A. "사용자는 연락처 앱에서 번호를 확인한다. 서버 프로세스 메모리는 재시작 시
 *    소실되고 폰 UI와도 무관하다. SoT를 ContactsContract에 두면 저장 체감과
 *    서버 재시작 내성이 동시에 확보된다. 서버는 STT 파싱만, 단말은 INSERT/조회."
 *
 * [면접 대비 주석 - 왜 Native Module인가]
 * Q. expo-contacts 같은 JS 라이브러리를 쓰면 안 되나요?
 * A. "데모 범위에서 쓰기/이름 조회만 필요해 의존성을 늘리지 않고
 *    ContactsBridgeModule.kt로 ContentProviderOperation을 직접 호출했다.
 *    권한은 PermissionsAndroid로 READ/WRITE_CONTACTS를 런타임 요청한다."
 */

import { NativeModules, PermissionsAndroid, Platform } from "react-native";

interface ContactsBridgeNative {
  saveContact(name: string, phoneNumber: string): Promise<boolean>;
  findPhoneByName(name: string): Promise<string | null>;
}

function getModule(): ContactsBridgeNative | null {
  if (Platform.OS !== "android") return null;
  return (NativeModules.ContactsBridgeModule as ContactsBridgeNative) ?? null;
}

async function ensurePermissions(write: boolean): Promise<boolean> {
  if (Platform.OS !== "android") return false;
  const perms = write
    ? [
        PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
        PermissionsAndroid.PERMISSIONS.WRITE_CONTACTS,
      ]
    : [PermissionsAndroid.PERMISSIONS.READ_CONTACTS];
  const result = await PermissionsAndroid.requestMultiple(perms);
  return perms.every((p) => result[p] === PermissionsAndroid.RESULTS.GRANTED);
}

/** 단말 주소록에 이름/번호를 저장한다. 성공 시 true. */
export async function savePhoneContact(name: string, phoneNumber: string): Promise<boolean> {
  const mod = getModule();
  if (!mod) {
    console.warn("[ContactsBridge] Android 모듈 없음 - 주소록 저장 스킵");
    return false;
  }
  const ok = await ensurePermissions(true);
  if (!ok) {
    console.warn("[ContactsBridge] READ/WRITE_CONTACTS 권한 거부");
    return false;
  }
  try {
    await mod.saveContact(name, phoneNumber);
    console.log(`[ContactsBridge] 주소록 저장: name=${name}, phone=${phoneNumber}`);
    return true;
  } catch (err) {
    console.warn("[ContactsBridge] 주소록 저장 실패:", err);
    return false;
  }
}

/** 단말 주소록에서 이름으로 번호를 찾는다. 없으면 null. */
export async function findPhoneContact(name: string): Promise<string | null> {
  const mod = getModule();
  if (!mod) return null;
  const ok = await ensurePermissions(false);
  if (!ok) return null;
  const phone = await mod.findPhoneByName(name);
  console.log(`[ContactsBridge] 조회: name=${name}, phone=${phone ?? "null"}`);
  return phone;
}
