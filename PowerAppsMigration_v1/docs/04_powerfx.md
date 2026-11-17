# 4. Power Fx 수식 적용과 검색 범위

`powerfx/*.fx`는 Studio **속성 수식 입력줄**에 넣는 수식입니다. 앞에 '='를 붙이지 않습니다. YAML 속성에서는 '=' 접두어가 필요합니다. 이 자료는 Power Fx 엔진/Studio 컴파일을 수행하지 않았습니다. 환경의 구분자·컨트롤 속성·필드 내부 이름을 확인해야 합니다.

| 파일 | 적용 위치 | 선행 조건 |
|---|---|---|
| 01 | App.OnStart | 앱을 만든 후 적용. OnStart 실행으로 변수 초기화 |
| 02 | txtSearch.OnChange | txtSearch classic input, DelayOutput=true |
| 03 | galAssets.Items | ITAssets 연결, JSON과 같은 내부 열 이름·타입 |
| 04 | 갤러리 상태 Label.Text | ThisItem 컨텍스트 |
| 05 | tmrRefresh.OnTimerEnd | Duration=30000, AutoStart/Repeat=true |
| 06 | 갤러리 행 OnSelect | AssetReadForEdit Flow 연결 및 03_UI의 입력 컨트롤 생성 |
| 07 | btnSave.OnSelect | AssetWrite Flow, 모든 입력 컨트롤, 서버 고유 제약·ETag 적용 |
| 08 | 정밀 검색 갤러리 Items | 완전한 colSnapshot만. 부분 수집 컬렉션에는 사용 금지 |
| 09 | lblExpiryPreview.Text | 날짜 포함 체크박스, 시작일, 개월 입력 |
| 10 | btnNew.OnSelect | 상세 입력 컨트롤 생성 |
| 11 | 샘플 모드 초기화 버튼 OnSelect | colSampleAssets는 서버 연결 검증이 아닌 UI 시험용 |

12_LoadSnapshot.OnSelect.fx는 정밀 모드 활성화 버튼에 적용합니다. complete=true일 때만 08 갤러리를 표시하세요.

## 위임을 고려한 기본 모드
03은 검색 문자열이 필드의 앞부분과 일치하는 접두어 모드입니다. 사용자가 기대하는 부분 문자열 모드와 같다고 표시하면 안 됩니다. 갤러리 위에 '접두어 검색'을 표시합니다. 정확한 S/N 조회는 `LookUp(ITAssets, SerialKey=varSearchKey)`로 할 수 있습니다.

대상 행에 Upper/Lower/Trim/DateDiff를 적용하거나, SharePoint Text 열에 부등호/Not을 쓰거나, Choice 하위 필드에 StartsWith를 적용하지 않았습니다. 정규화는 입력/저장 때 수행하고 날짜는 원본 열과 상수 범위로 비교합니다. Microsoft의 SharePoint 위임 표를 기준으로 작성했으나, 실제 Studio 경고와 Monitor 요청 검증을 통과해야 위임됨으로 판정합니다. [SharePoint 연결과 위임](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/connections/connection-sharepoint-online)

**검증:** 데이터 행 한도를 1로 설정하고 대상 레코드를 첫 행 밖에 둡니다. 그 다음 2,001건 이상의 가상 목록으로 검색·정렬·정확 S/N 조회를 시험합니다. 단순히 한도를 올리거나 청색 경고를 숨기는 것으로 완전성을 보장하지 않습니다. 5,000건 이상의 목록은 SharePoint 뷰 임계값과 인덱스 조합도 별도 확인합니다.

## 기존 방식과 동일한 정밀 모드
기존 Python은 모든 관리 열을 연결하고 공백으로 나눈 단어가 모두 부분 문자열로 포함되는지 검사합니다. 이 동작은 08 수식으로 소규모 **완전 스냅샷**에서 재현합니다.

AssetSearchSnapshot Flow가 페이지를 끝까지 읽고, 정한 상한/응답 크기 안에 모두 들어오는 경우에만 Complete=true와 RecordsJson을 반환해야 합니다. Canvas에서 JSON을 타입 있는 collection으로 변환한 뒤 varSnapshotComplete=true로 바꿉니다. 상한 초과·페이지 실패·원본 변경으로 일관성이 확인되지 않으면 결과를 '전체 검색'처럼 보여주지 않습니다. 접두어 모드나 서버 검색/대조 작업으로 유도합니다.

샘플 시험: 11 파일 실행 후 `ClearCollect(colSnapshot,colSampleAssets); Set(varSnapshotComplete,true)`로 08을 적용합니다. 실제 연결에서 이 코드를 그대로 Complete=true로 강제하면 안 됩니다.

## 수량/중복/날짜
- 전체 카드에 `CountRows(Filter(ITAssets,...))`를 그대로 사용하지 않습니다. ITAssetSummary의 Complete=true 집계와 시각을 보여주고 없으면 '집계 중'으로 표시합니다.
- 중복 LookUp은 사용자 안내용입니다. 경쟁 요청 두 개가 동시에 같은 S/N을 만들 때는 SharePoint 고유 제약이 최종 방어선입니다.
- 오류나 HTTP 412에서 폼을 초기화하지 않습니다. 07은 성공 때만 모달을 닫습니다.
- 기본 날짜 Today()는 기존 앱처럼 사용자 PC의 날짜입니다. 한국 이외 시간대도 운영하면 서버의 Korea Standard Time 기준일을 설정 Flow에서 전달하도록 변경하고 경계 테스트를 해야 합니다.
- 잔여일 Label은 `If(ThisItem.HasExpiry,Text(DateDiff(varToday,ThisItem.ExpiryDate,TimeUnit.Days)),"미등록")`입니다. 폐기 표시 우선순위는 04를 따릅니다.
