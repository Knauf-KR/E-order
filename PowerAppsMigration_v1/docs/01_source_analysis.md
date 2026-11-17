# 1. 기존 소스와 Excel 구조의 실제 분석

분석 대상: 로컬 `ITAssetManager` v0.5의 app.py, storage.py, reconcile.py, sap_ui.py, sync_policy.py, portable.py, windowed.pyw 및 기존 테스트, 사용자가 제공한 자산 Excel과 SAP Asset List. 실제 파일은 로컬에서만 열었습니다. 공개 자료에는 실집계나 개별 자산 값을 넣지 않았으며 구체적 실집계는 대화에서 별도로 전달합니다.

## 코드에서 확인한 동작
| 근거 | 실제 동작 | 전환 시 유의점 |
|---|---|---|
| storage.Store.rows | 지정된 5개 시트, 3행 헤더, 4행부터 B:R. C:I 중 비수식 값이 있는 행만 자산으로 판단 | 서식이 있는 max_row나 Excel No.를 자산 수/고유 ID로 쓰면 안 됨 |
| app.App.refresh | 모든 원본 관리 열을 연결하고 각 검색어가 부분 문자열로 모두 존재하는지 검사 | StartsWith로 바꾸면 동일 기능이 아님. 정밀 모드를 별도 설계 |
| app.location_key | Dan/Dangjin/당진 등을 조회 시 같은 위치로 취급 | 원문 LocationRaw를 남기고 LocationKey를 별도로 생성 |
| storage.Store.status | 폐기 우선 → 날짜 미등록 → 만료 → 30/60/90일 → 정상 | 오늘 만료는 30일 이내, 이미 지난 날짜만 만료. 범위 필터는 누적 |
| storage.Store.expiry | 만료일이 유효하면 사용, 아니면 시작일+개월로 계산 | 기존 수식 캐시와 '#VALUE!'를 그대로 Date 열에 넣으면 안 됨 |
| storage.Store.apply | S/N 필수, trim+casefold 중복 검사. 기존 수식은 편집하지 않음 | SAP 대조의 NFKC/공백 제거와 기존 UI 정규화 규칙이 다름. 표준화 시 재검사 필요 |
| app.checks | S/N/모델/위치/사무직 사용자 누락, 날짜 순서, Excel 오류 검사 | 점검 상태는 원본 보존과 함께 마스터 플래그/검토 목록으로 분리 |
| storage.relocate | 행을 당기지 않고 원본 B:R을 비움. User/User KOR를 맞추고 없는 열은 비고에 보관 | 신규 앱에서는 동일 ID의 상태/구분 변경. 행 이동·수식 복사 불필요 |
| app.Editor | 조회 전용 팝업 → 수정. 기본/사용자·위치/만료/비고 탭 | Canvas 내 모달 및 모바일 상세 화면으로 재현 |
| app.monitor_* / save | 로컬 해시를 3초마다 확인, 2회 안정 후 갱신. 편집 보호. 적용 후 0.8초 자동 저장과 파일 백업 | 파일 감시/덮어쓰기 대신 항목 단위 저장, ETag 충돌 처리, 버전 이력 |
| reconcile.SapBook | Asset/Asset description 시트 인식. 256열까지만 헤더 검색, 실제 열만 읽음 | SAP K-GAAP의 과도한 서식 폭을 전체 데이터로 확장하면 메모리 낭비 |
| reconcile.compare | 단일 회계 시트 기준 양방향 S/N 대조. 중복·폐기·번호 불일치·추출 불가를 분리 | SAP 추출/대량 비교는 Canvas 로컬 ForAll로 완전히 옮길 수 없음 |
| portable / launch.vbs | 실행 위치의 고정 파일명, PC별 런타임 | Canvas URL·회사 로그인으로 대체. Python/VBS 설치 불필요 |

## Excel 열 매핑
| 열 | 공통 의미 | 마스터 필드 |
|---|---|---|
| B | No. (재사용/중복 가능) | LegacyNo. 고유 ID 아님 |
| C | SAP번호 | SAPAssetNumber: Text (앞자리 0 보존) |
| D/E/F/G | PC Name / S/N / Type / Model | PCName / SerialNumber+SerialKey / DeviceTypeRaw+DeviceType / Model |
| H | Location | LocationRaw + LocationKey |
| I/J | 일반 시트 User KOR / Lan Connector | AssignedUserKOR / LanConnectorRaw |
| I/J | **Plant Desktop: L. Detail / User** | **LocationDetail / AssignedUserKOR** |
| K | 일반 소모품 지급 / 창고 Check List | ConsumablesRaw / ChecklistRaw 각각 구분 |
| L/M | User ENG / AD Account | AssignedUserENG / ADAccount |
| N/O/P | 시작일 / 만료일 / 사용기간 | StartDate / ExpiryDate / UsageMonths + 원문·근거 |
| Q/R | 잔여개월 / Remark | LegacyRemainingText / Remarks. 실제 잔여일은 화면 계산 |

원본에는 자산 시트 외 `현황`, `SN검사`가 있습니다. 집계·파생 결과이므로 중복 이관하지 않고 신규 앱/서버 집계로 대체합니다. 이번 파일에서는 R열 이후 실데이터가 없는 것을 로컬로 확인했습니다. 추후 파일에서는 추가 열과 기존 행 판정에서 빠지는 행을 재점검해야 합니다.

## 보존/정제 원칙
- S/N 중복을 최신 No.나 시트 순서로 자동 통합하지 않습니다. 서로 다른 행은 staging에 남깁니다.
- Type의 오타와 공란을 임의로 Laptop으로 추정하지 않습니다. Unknown+원문+점검 표시로 유지합니다.
- 미취득은 날짜가 아닌 AcquisitionState로 표현합니다. '#REF!' 등은 날짜·계정의 정상 값으로 취급하지 않고 LegacyMetadata에 값/수식을 보존합니다.
- 원본 No./행 번호/빈 날짜, 사용자 한국어·영문명, 지급 표시의 원문 의미를 유지합니다.
