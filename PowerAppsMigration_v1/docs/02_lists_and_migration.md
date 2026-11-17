# 2. SharePoint Lists 데이터 구조와 이관

전체 필드·타입·필수·인덱스·고유 여부는 `schema/sharepoint-lists.json`이 기준입니다. 영어 내부 이름으로 먼저 생성하고 한국어 표시명을 지정합니다. 기존 열을 표시명만 바꾸면 내부 이름이 달라질 수 있으므로 연결 후 확인합니다.

## 목록 구성
| 목록 | 용도 | 권한/쓰기 |
|---|---|---|
| ITAssets | 단일 자산 마스터, 폐기 포함 | 조회 그룹 read. 권장 쓰기는 검증 Flow만 허용 |
| ITAssetStaging | 원본 행 전체, 제안 값, 중복/오류 검토 | 이관 담당자만 쓰기/원문 접근 |
| ITLocations | LocationKey/Title/SortOrder. ALL은 필터 전용 | 관리자가 기준값 관리 |
| ITAssetSummary | 서버가 페이지 순회해 만든 전체 집계+기준시각+Complete | 앱은 읽기만. 정확한 수량에 CountRows(ITAssets) 사용 금지 |
| ITAssetEvents | 이동·폐기·삭제 사유/요청자/시각 | Flow append. 버전 이력을 대체하는 원자적 감사 로그는 아님 |
| ITSAPBatches / ITSAPResults | SAP 대조 작업과 결과 | 2단계. BatchKey/StatusCode 인덱스 |
| ITAssetImports (문서 라이브러리) | SAP 원본 및 검토 산출물 | 2단계, 승인된 사내 사이트만 사용 |

관계: ITAssetEvents.AssetId → ITAssets.ID, ITSAPResults.BatchKey → ITSAPBatches.BatchKey. 숫자/텍스트 참조를 쓰므로 Flow가 존재 여부를 확인합니다. 여러 목록 갱신은 SharePoint 단일 트랜잭션이 아닙니다.

## 핵심 필드 결정
- AssetKey: GUID 텍스트 고유, SharePoint ID: 플랫폼 PK. SAP번호와 Excel No.는 키가 아닙니다.
- SerialNumber: 원문, SerialKey: 공백 제거·대문자 ASCII 정규화. 마스터 SerialKey는 **필수·인덱스·고유**로 설정합니다. 폐기/논리 삭제도 같은 S/N을 재등록하지 않고 기존 자산을 복원합니다.
- AssetGroup(Office/Shared/Plant/Unassigned)와 LifecycleState(InUse/Stock/Retired)를 분리합니다. 창고·폐기 원본의 과거 사용 구분은 알 수 없으므로 Unassigned로 시작합니다. 이후 창고 이동 시 기존 사용 구분을 유지합니다.
- 구분·종류·표준 위치는 **단일 줄 Text**로 저장하여 검색/정렬/필터를 단순화합니다. 드롭다운 표시 이름과 저장 코드는 구분합니다. Text이므로 서버에서 허용 코드를 강제 검증해야 합니다.
- 만료일은 Date Only. 유효한 원본 만료일 → 시작일+개월 → Unknown 순으로 해석합니다. ExpirySource와 LegacyExpiryText를 보존하고 HasExpiry를 같은 저장 요청에서 갱신합니다.
- `ExpiryStatus='30일 이내'` 같은 날짜 의존 문자열을 영구 저장하지 않습니다. 화면은 날짜 비교, 요약은 기준일로 재집계합니다.
- LegacyMetadata는 B:R 값과 수식 보존 JSON입니다. 임의로 실행하지 않습니다. 원본 파일도 회사 내부에 읽기 전용 보존합니다.
- SharePoint DateOnly와 UTC API 반환을 혼동하지 않도록 사이트/Flow 업무 시간대를 Korea Standard Time으로 설정하고 화면에는 yyyy-MM-dd를 전달합니다.

## 이관 단계
1. 현재 Excel과 기존 프로그램을 읽기 전용 스냅샷으로 보관하고 변경 동결 시점을 정합니다. 원본을 자동 변경하지 않습니다.
2. 샘플 전용 사이트에 JSON 스키마대로 목록을 생성합니다. 초기 사용자에게 실제 데이터 접근 권한을 주지 않습니다.
3. `tools/make_samples.py`의 가상 20행으로 매핑·누락/중복·날짜·권한·동시 저장을 시험합니다. 원본 20행 = ready 16 + S/N 검토 4이며 staging에서 한 행도 잃지 않습니다.
4. 실제 변환은 회사 로컬 PC에서 `convert_excel.py --input ... --output <배포폴더밖>`으로 실행합니다. 이 도구에는 네트워크/업로드 코드가 없습니다.
5. 전체 원본을 staging에 적재하고 ReviewState를 검토합니다. 중복 그룹은 어느 한 행을 자동 삭제하지 않습니다. S/N 확정, 동일 장비 이력 통합 승인, 잘못된 S/N 수정 등을 담당자가 결정합니다. 수정 근거를 보존합니다.
6. Ready/Approved만 ITAssets로 승격합니다. 원본 값·수식과 SourceSheet/SourceRow를 남깁니다. AssetKey로 동일 입력 재시도의 중복 생성 여부를 확인하고 SerialKey 제약도 유지합니다.
7. Unknown 종류, 위치·사용자·날짜 누락은 숨기지 않고 점검 플래그를 유지합니다. 타이핑 오류 정정은 승인 이력과 함께 수행합니다.
8. **마스터 수 + 보류 staging 수 = 전체 원본 행 수**를 확인합니다. 상태/시트·S/N·SAP번호·한글/영문 사용자·특수 열을 표본 대조합니다. SourceKey 기준 재실행 결과도 비교합니다.
9. 제한된 사용자 UAT → 변경 동결 후 최종 차이 재이관 → Excel 편집을 종료합니다. 전환 후 SharePoint를 단일 원본으로 삼으며 Excel과 양방향 자동 동기화하지 않습니다.
10. 롤백 시 앱 쓰기를 중지하고 전환 이후 항목 변경을 내보내 검토한 다음 승인된 Excel 스냅샷으로 돌아갑니다. 운영 중 Excel과 Lists를 동시에 편집하지 않습니다.

## 인덱스와 규모
SerialKey/AssetKey는 고유 인덱스, AssetGroup/LifecycleState/LocationKey/DeviceType/PCName/ExpiryDate/HasExpiry/HasDataIssues/IsDeleted 등에 인덱스를 계획했습니다. 인덱스의 존재가 모든 OR 검색이나 조합 쿼리를 5,000건 뷰 임계값에서 안전하게 만드는 것은 아닙니다. 대량이면 먼저 상태/사이트 등 선택적 조건으로 제한하고 실제 요청을 시험합니다. 넓은 OR 검색이 병목이면 검색 서버나 Dataverse 전환을 별도 결정합니다. [Microsoft: 대량 목록 필터](https://support.microsoft.com/en-us/sharepoint/data-and-lists/use-filtering-to-modify-a-sharepoint-view)

## 생성 도구
`provision-lists.ps1`는 PnP.PowerShell 커뮤니티 모듈 기반 선택 도구입니다. 기본 dry-run이며 -Apply 이전에는 테넌트를 수정하지 않습니다. 사내 승인 ClientId/권한, PowerShell 버전을 확인하세요. 실행 검증은 하지 않았으므로 개발 사이트에서만 먼저 사용합니다. 모듈을 쓰지 않으면 Lists UI로 동일한 필드를 생성할 수 있습니다. 생성만으로 앱·Flow·권한·이관이 완료되지 않습니다.
