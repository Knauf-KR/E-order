# 7. 서버 흐름·권한·동시 저장 계약

아래는 **실제 Flow를 만들기 위한 계약과 작업 순서**입니다. 이 폴더에 가져오기 가능한 Flow 솔루션은 없습니다. Power Apps (V2) 트리거의 입력 순서·응답 이름을 정확하게 만들고 앱에 Flow를 연결해야 합니다.

## 권한 기본 모델
- 초기 개발은 가상 데이터 사이트로 한정합니다. 운영 사이트/실제 파일 업로드는 별도 승인 후 전환합니다.
- 앱 사용자=회사 Entra 그룹. 읽기 사용자에게 ITAssets/Locations/Summary 읽기, 쓰기는 승인된 Flow 연결만 허용합니다. 사이트 기본 Members에 Edit가 남아 있으면 앱을 우회할 수 있으므로 목록 권한도 확인합니다.
- AssetWrite 실행 권한은 자산 편집 그룹, 이관/논리 삭제/복구 Flow는 관리자 그룹으로 제한합니다. 버튼 Visible/DisplayMode는 보안 경계가 아닙니다.
- 서비스 연결을 쓰면 SharePoint Modified By는 서비스 계정일 수 있습니다. 요청자는 플랫폼에서 검증한 호출 사용자로 기록하며 payload의 이메일을 권한 판정에 신뢰하지 않습니다. 실행 전용 사용자/연결 정책을 관리자와 구성합니다.
- SharePoint/Power Apps/Power Automate의 표준 커넥터 사용 권한도 회사 라이선스·DLP에서 확인합니다. 이 설계만으로 라이선스가 충족된다고 확정하지 않습니다.

## A. AssetReadForEdit
입력: `assetId` (Text, 앱 Run의 첫 번째 인수). 응답: status/message/etag/assetJson (모두 Text).
1. 정수 ID와 호출 권한을 검증합니다. 삭제된 항목은 관리자 복구 기능 외 조회/수정을 거절합니다.
2. **Send an HTTP request to SharePoint**:
   - Method GET
   - URI `_api/web/lists/getbytitle('ITAssets')/items(<검증된 ID>)`
   - Accept `application/json;odata=verbose`
3. 같은 응답의 `d.__metadata.etag`와 필드 값을 사용합니다. 별도의 Get item으로 새 값을 읽고 이전 ETag를 섞지 않습니다.
4. JSON 객체의 `ID`를 REST `Id`에서 명시적으로 매핑하고 custom 필드를 내부 이름으로 담습니다. Date Only는 사이트/Korea Standard Time으로 정규화한 `yyyy-MM-dd` 또는 null을 반환합니다. 응답 JSON은 06 수식의 모든 필드가 있어야 합니다.
5. Respond to a Power App or flow: status=Ok, message="", etag=원문 그대로(따옴표 포함), assetJson=객체를 JSON 문자열로 변환.

실패 시 status=NotFound/Forbidden/Error, message=사용자 안내, etag="", assetJson="{}"를 반환합니다. ID에 SQL/OData 문자열을 직접 삽입하지 않도록 먼저 정수 검증합니다.

## B. AssetWrite
입력 순서: `payloadJson` Text → `expectedEtag` Text → `assetId` Text. 응답: status/message/id/etag (모두 Text). 07 수식과 동일합니다.

### 검증과 정규화
- JSON Schema/Parse JSON으로 허용된 필드만 받습니다. AssetKey, IsDeleted, SourceSheet/Row, LegacyMetadata, IssueCodes, HasExpiry, SerialKey, LastRequestId를 클라이언트 임의 값으로 덮어쓰지 않습니다.
- S/N: 공백/탭/CR/LF/NBSP 제거와 대문자화 후 ASCII `[A-Z0-9-]` 및 길이 1~255를 검사합니다. 전각/다른 문자 입력은 확인을 요청합니다. O/0은 치환하지 않습니다.
- AssetGroup/LifecycleState/DeviceType/AcquisitionState 코드, LocationKey의 존재/SelectableForAsset을 검사합니다. InUse+Unassigned는 새 저장에서 거절합니다.
- 사용기간은 정수 1~1200 또는 null. 실제 달력 날짜, 시작일/만료일 순서, 텍스트 길이, 미취득+유효 시작일 모순을 검증합니다.
- ExplicitExpiryDate가 있으면 사용, 없고 StartDate+UsageMonths가 유효하면 달력 말일을 보정해 계산합니다. 그 외 null. ExpirySource/HasExpiry를 같은 쓰기에서 갱신합니다.
- 서버 계산도 시작월 1일에 개월을 더하고, 마지막 날과 원래 일을 min으로 취합니다. 1/31+1개월, 윤년 2/29+12개월 시험 필수입니다.
- 기존 미해결 원본 오류는 검토 승인 없이 지우지 않습니다. 신규 누락 점검과 합쳐 HasDataIssues/IssueCodes를 유지합니다.

### 새 자산
assetId가 빈 문자열이면 서버에서 AssetKey GUID를 만들고 목록의 실제 ListItemEntityTypeFullName을 사용하여 REST POST로 생성합니다. SerialKey의 고유 제약이 최종 중복 방어입니다. 조회 후 생성의 두 단계 검사만으로 고유성을 보장하지 않습니다.

### 기존 자산: 원자적 충돌 거절
- assetId가 있으면 expectedEtag가 필수입니다. `*`는 허용하지 않습니다.
- Method POST, URI `_api/web/lists/getbytitle('ITAssets')/items(<ID>)`
- Headers: `IF-MATCH: <읽을 때 받은 expectedEtag>`, `X-HTTP-Method: MERGE`, `Accept: application/json;odata=verbose`, `Content-Type: application/json;odata=verbose`.
- body는 `__metadata.type`에 해당 목록의 실제 ListItemEntityTypeFullName을 넣고, 허용 필드+서버 계산 필드만 포함합니다. 목록 타입 이름을 추측하지 말고 목록 REST 메타데이터에서 조회합니다.
- 사전 Modified 비교가 아니라 **조건부 업데이트 요청 자체**로 충돌을 차단합니다. HTTP 412는 Conflict로 반환합니다. 앱은 입력/모달을 유지합니다.
- S/N 고유 제약 위반은 테넌트에서 관측한 SharePoint 오류 코드/본문을 근거로 DuplicateSerial로 분류합니다. 모든 HTTP 400을 중복이라고 처리하지 않습니다. 기타 오류는 ValidationError/Forbidden/Error로 안내합니다.

성공하면 status=Ok, id=저장 ID. etag는 업데이트 뒤 재조회한 최신 ETag 또는 빈 문자열입니다(현재 UI는 성공 시 닫으므로 재수정은 새 Read로 시작). 이 값을 이전 편집 스냅샷에 덧붙여 계속 쓰지 않습니다.

### 이벤트/불확실한 응답
업무 상태 전환 사유와 RequestId를 받고 ITAssetEvents에 기록합니다. 자산 업데이트와 이벤트 추가는 원자적 트랜잭션이 아닙니다. 주기적 보정/감사 작업을 두거나 엄격한 감사가 필요하면 Dataverse/트랜잭션 백엔드를 별도 검토합니다. 성공 마스터에는 LastRequestId를 기록합니다.

네트워크 타임아웃은 '실패하여 저장되지 않음'을 뜻하지 않습니다. 앱은 Unknown으로 표시하고 RequestId를 남깁니다. 마스터의 LastRequestId/이벤트/실제 값을 다시 조회해 완료 여부를 확인한 뒤 재시도합니다. 무조건 같은 생성 요청을 반복하지 않습니다.

Flow는 Try/Catch scope와 실패/시간 초과 Run after를 구성하여 가능한 모든 경로에서 명시적 응답을 반환합니다. 연결 자체가 끊겨 응답이 없을 때도 앱이 varSaving을 해제하고 입력을 보존하도록 07에 IfError가 있습니다.

## C. 위치 이동/폐기/논리 삭제
- 이동/폐기는 AssetWrite에 새로운 LifecycleState와 변경 사유를 담아 동일 ID에 저장합니다. UI에 txtActionReason을 추가하고 상태가 바뀔 때 필수로 받습니다.
- 폐기 확인일은 사용자가 확인한 날짜를 별도 승인 로직으로 기록합니다. Excel 폐기 시트에 있었다고 오늘 날짜로 과거 폐기일을 채우지 않습니다.
- 삭제는 관리자 전용 AssetSoftDelete Flow로 분리합니다. 입력 ID/ETag/사유를 검사하고 동일 IF-MATCH 방식으로 IsDeleted=true를 기록합니다. 복구는 같은 행을 되살립니다. SharePoint Remove를 일반 앱에 노출하지 않습니다.

## D. AssetSearchSnapshot (소규모 정밀 검색)
입력 없음. 출력 `complete` Boolean, `recordsJson` Text, `message` Text, `snapshotAt` Text.
- 권한이 허용한 전체 ITAssets 행을 조회합니다. 서버 페이지를 끝까지 읽고 중복 ID를 제거/검증합니다. 응답 항목의 날짜는 yyyy-MM-dd, Boolean/Number는 실제 타입으로 유지합니다.
- 초기 상한은 **2,000행 및 테스트한 응답 바이트 한도**로 명시합니다. 상한 초과, 남은 페이지, 실패/접근 누락이면 complete=false, recordsJson="[]". 부분 데이터를 전체처럼 반환하지 않습니다.
- 스냅샷 전후 목록 수정 정보를 비교해 변화를 감지하면 재시도/실패 안내합니다. SharePoint 다중 페이지 읽기는 트랜잭션 시점 일관성을 보장하지 않습니다. complete는 전체 페이지 수집 조건이며 강한 데이터베이스 snapshot 보장이 아닙니다.
- 앱은 12 수식으로 타입 변환 후에만 정밀 모드를 활성화합니다. 대규모이면 서버 검색 작업 또는 Dataverse 검색으로 대체합니다.

## E. Summary/Export
Summary Flow는 모든 페이지를 집계하여 ITAssetSummary Global에 Complete/CalculatedAt/BusinessDate/CountsJson을 씁니다. 실수로 일부 페이지만 더한 수량을 Complete=true로 저장하지 않습니다. 한국 날짜 경계에 재계산하고 변경 후 갱신도 큐잉합니다. Canvas에는 기준 시각을 표시합니다.

Export Flow는 화면의 **필터 값**을 받고 서버에서 다시 조회합니다. 사용자가 전달한 임의 OData를 그대로 실행하지 않습니다. CSV의 `=,+,-,@` 시작 문자열을 안전하게 처리하고 파일은 권한이 적용된 사내 라이브러리에 만듭니다. 파일 링크도 호출 사용자 권한을 확인합니다.

## F. SAP 2단계 구현
1. 원본을 사내 ITAssetImports에 업로드하고, K-GAAP/IFRS/HGB 중 하나를 선택하여 배치를 생성합니다. 같은 자산의 회계 시트 중복 집계를 막습니다.
2. 기존 reconcile.py의 알고리즘을 서버 추출기로 포팅합니다. Excel Online의 'List rows present in a table'은 원본이 표가 아닐 수 있으므로 그대로 사용할 수 없습니다. Office Script로 실제 헤더/열을 읽어 추출하거나, 승인된 내부 실행 환경에서 기존 Python 추출을 수행합니다. 원본 파일을 수정하지 않습니다.
3. S/N 전용 열을 우선, 없으면 검증된 설명 패턴에서 추출합니다. 없는 S/N을 장비 모델명으로 만들지 않습니다. 미인식 모델과 묶음 자산은 검토 대상입니다.
4. ITAssets 전체와 같은 정규화로 양방향 대조합니다. 대규모 ID별 Lookup/Canvas ForAll은 피하고 서버에서 인덱스/페이지를 처리합니다.
5. 기존 상태(일치/IT 목록에 없음/폐기목록/SAP번호 불일치/중복/SN 확인/종류 확인/SAP 미확인/대상외)를 별도 코드로 저장합니다. BatchKey/StatusCode 필터로 조회합니다.
6. 배치에는 기준 파일·회계 시트·IT 기준 시각/변경 감지 여부·완료 여부를 기록합니다. 원본 SAP 파일 변경 시 새 배치로 실행합니다.

이 문서는 SAP 포팅 계약입니다. 실제 서버 추출기/Office Script/완성된 SAP 업로드 Canvas 화면을 구현·검증한 것으로 표시하지 않습니다. 초기 배포의 검색·상세·중복 검증과 별도 완료 기준으로 관리합니다.
