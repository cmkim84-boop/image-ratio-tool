/*
  Q 이미지 편집기 - 사용 의견 받는 구글 시트용 코드 (앱스 스크립트)

  [설치 방법]
  1. 구글 시트를 새로 만든다. (이름 예: Q 이미지 편집기 의견)
  2. 위 메뉴 [확장 프로그램] > [Apps Script] 를 연다.
  3. 기본으로 들어 있는 코드를 모두 지우고, 이 파일 내용을 통째로 붙여 넣는다. 저장(디스크 아이콘).
  4. 오른쪽 위 [배포] > [새 배포] 를 누른다.
  5. 톱니바퀴 > 유형 선택에서 [웹 앱] 을 고른다.
       - 다음 사용자로 실행: 나
       - 액세스 권한이 있는 사용자: 모든 사용자
  6. [배포] 를 누르고, 권한 승인 창이 뜨면 계정을 고르고 [고급] > [(안전하지 않음) 이동] > [허용] 을 누른다.
     (내가 만든 코드라서 나오는 경고다)
  7. 마지막에 나오는 '웹 앱 URL'(https://script.google.com/macros/s/.../exec)을 복사한다.
  8. 그 주소를 Claude 에게 알려 주면 프로그램에 넣어서 새 파일을 만들어 준다.

  [나중에 이 코드를 고쳤을 때]
  [배포] > [배포 관리] > 연필 아이콘 > 버전을 '새 버전' 으로 > [배포] 해야 반영된다. (주소는 그대로)
*/

const SHEET_NAME = "의견";

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    const d = JSON.parse(e.postData.contents);

    const rating = Math.max(0, Math.min(5, parseInt(d.rating, 10) || 0));
    const features = Array.isArray(d.features)
      ? d.features.slice(0, 10).map(String).join(", ").slice(0, 100)
      : "";
    const comment = String(d.comment || "").slice(0, 300);
    const version = String(d.version || "").slice(0, 20);

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sh.getLastRow() === 0) {
      sh.appendRow(["시간", "별점", "자주 쓴 기능", "의견", "프로그램 버전"]);
      sh.setFrozenRows(1);
    }
    const when = Utilities.formatDate(new Date(), "Asia/Seoul", "yyyy-MM-dd HH:mm");
    sh.appendRow([when, rating, safe_(features), safe_(comment), safe_(version)]);
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

// 브라우저로 주소를 열어 봤을 때 "작동 중" 확인용
function doGet() {
  return json_({ ok: true, info: "Q 이미지 편집기 의견 받는 곳" });
}

// 시트에서 =, +, -, @ 로 시작하는 글이 수식으로 실행되지 않게 막는다
function safe_(s) {
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
