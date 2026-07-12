package com.minchodan.app

import android.content.ContentProviderOperation
import android.content.ContentResolver
import android.provider.ContactsContract
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

// ==========================================
// 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
// 음성 연락처 저장을 서버 RAM이 아니라 Android 주소록(ContactsContract)에 기록한다.
// ==========================================
//
// 💡 [면접 대비 주석]
// Q. 왜 서버 ContactStore만 쓰지 않고 단말 주소록에 쓰나요?
// A. "ContactStore는 프로세스 메모리라 서버 재시작 시 소실되고, 사용자는 폰
//    연락처 앱에서 번호를 확인합니다. 저장의 체감 위치는 OS 주소록이므로
//    WRITE_CONTACTS로 RawContact를 추가합니다. 서버는 의도/번호만 파싱하고
//    실제 영속화는 단말에 위임하는 구조입니다(dial_action과 같은 역할 분리)."
//
// 💡 [면접 대비 주석 - ContentProviderOperation 배치]
// Q. insert를 세 번 따로 호출하지 않고 applyBatch를 쓰는 이유는요?
// A. "RawContact 생성 → StructuredName → Phone은 원자적으로 묶여야 한다.
//    withValueBackReference로 방금 삽입한 RAW_CONTACT_ID를 Data 행에 연결하고,
//    중간에 실패하면 배치 전체가 롤백되어 이름만 남는 고아 레코드를 막는다."
//
// 💡 [면접 대비 주석 - ACCOUNT_TYPE/NAME null]
// Q. 계정 타입을 null로 넣는 게 맞나요?
// A. "로컬(기기 전용) 연락처로 저장한다. Google 계정 동기화 계정에 묶지 않아
//    데모/사이드로드 환경에서 계정 선택 UI 없이 즉시 연락처 앱에 보이게 한다."
//
// [TH HARDCODE] findPhoneByName은 완전 일치 우선, 부분 일치 폴백(조사/호칭 누락 대비).
class ContactsBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName(): String = "ContactsBridgeModule"

    @ReactMethod
    fun saveContact(name: String, phoneNumber: String, promise: Promise) {
        try {
            val trimmedName = name.trim()
            val trimmedPhone = phoneNumber.trim()
            if (trimmedName.isEmpty() || trimmedPhone.isEmpty()) {
                promise.reject("CONTACTS_INVALID", "name/phone empty")
                return
            }
            val ops = ArrayList<ContentProviderOperation>()
            val rawContactIndex = 0
            ops.add(
                ContentProviderOperation.newInsert(ContactsContract.RawContacts.CONTENT_URI)
                    .withValue(ContactsContract.RawContacts.ACCOUNT_TYPE, null)
                    .withValue(ContactsContract.RawContacts.ACCOUNT_NAME, null)
                    .build(),
            )
            ops.add(
                ContentProviderOperation.newInsert(ContactsContract.Data.CONTENT_URI)
                    .withValueBackReference(ContactsContract.Data.RAW_CONTACT_ID, rawContactIndex)
                    .withValue(
                        ContactsContract.Data.MIMETYPE,
                        ContactsContract.CommonDataKinds.StructuredName.CONTENT_ITEM_TYPE,
                    )
                    .withValue(ContactsContract.CommonDataKinds.StructuredName.DISPLAY_NAME, trimmedName)
                    .build(),
            )
            ops.add(
                ContentProviderOperation.newInsert(ContactsContract.Data.CONTENT_URI)
                    .withValueBackReference(ContactsContract.Data.RAW_CONTACT_ID, rawContactIndex)
                    .withValue(
                        ContactsContract.Data.MIMETYPE,
                        ContactsContract.CommonDataKinds.Phone.CONTENT_ITEM_TYPE,
                    )
                    .withValue(ContactsContract.CommonDataKinds.Phone.NUMBER, trimmedPhone)
                    .withValue(
                        ContactsContract.CommonDataKinds.Phone.TYPE,
                        ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE,
                    )
                    .build(),
            )
            reactApplicationContext.contentResolver.applyBatch(ContactsContract.AUTHORITY, ops)
            promise.resolve(true)
        } catch (e: SecurityException) {
            promise.reject("CONTACTS_PERMISSION", e.message)
        } catch (e: Exception) {
            promise.reject("CONTACTS_SAVE_ERROR", e.message)
        }
    }

    @ReactMethod
    fun findPhoneByName(name: String, promise: Promise) {
        try {
            val query = name.trim()
            if (query.isEmpty()) {
                promise.resolve(null)
                return
            }
            val resolver: ContentResolver = reactApplicationContext.contentResolver
            val projection = arrayOf(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
            )
            resolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                null,
                null,
                null,
            ).use { cursor ->
                if (cursor == null) {
                    promise.resolve(null)
                    return
                }
                val nameIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val phoneIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                var exact: String? = null
                var partial: String? = null
                while (cursor.moveToNext()) {
                    val display = cursor.getString(nameIdx) ?: continue
                    val phone = cursor.getString(phoneIdx) ?: continue
                    if (display == query) {
                        exact = phone
                        break
                    }
                    if (partial == null && (display.contains(query) || query.contains(display))) {
                        partial = phone
                    }
                }
                promise.resolve(exact ?: partial)
            }
        } catch (e: SecurityException) {
            promise.reject("CONTACTS_PERMISSION", e.message)
        } catch (e: Exception) {
            promise.reject("CONTACTS_LOOKUP_ERROR", e.message)
        }
    }
}
