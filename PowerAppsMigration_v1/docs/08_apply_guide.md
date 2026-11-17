# 8. Power Apps에 실제 적용하는 단계

## 0. 준비/범위
회사 개발 Power Platform 환경, 샘플 SharePoint 사이트, Maker 권한, 승인된 연결 계정/Entra 그룹을 준비합니다. 이 자료는 테넌트에 로그인하거나 목록·Flow·Canvas 앱을 생성하지 않았습니다. 처음에는 가상 데이터만 사용합니다.

## 1. 샘플 Lists 생성
1. Lists UI에서 Blank list로 ITAssets 등 목록을 만듭니다. `schema/sharepoint-lists.json`과 같은 **영문 내부 이름**으로 열을 생성한 뒤 한국어 표시명을 붙입니다. 기본 Title은 필수 해제합니다.
2. Date는 Date only, Note는 일반 여러 줄, Boolean은 Yes/No, 코드 필드는 Choice가 아닌 Text입니다.
3. SerialKey/AssetKey/SourceKey 등의 고유 제약, 인덱스, 버전 이력을 설정합니다. 고유 제약은 중복 이관 전에 켜고 중복 원본은 staging에 남깁니다.
4. 선택 도구를 쓰면 PowerShell 7 및 승인된 PnP.PowerShell을 준비하고 `provision-lists.ps1`의 dry-run 결과를 먼저 확인합니다. -Apply는 샘플 사이트에서만 실행합니다.
5. 목록 권한을 확인합니다. 앱 조회자에게 원본 staging JSON이나 관리 Flow 쓰기 권한을 넓게 주지 않습니다.

## 2. 가상 데이터 적재
`sample/ITAssets.sample.xlsx`는 가상 원본 20행, staging JSON은 20행, assets_ready JSON/CSV는 S/N 보류를 제외한 16행입니다. 실제 자산 파일과 혼동하지 않도록 DEMO 접두어를 유지합니다.

생성한 기존 목록에 `import-samples.ps1`의 dry-run을 확인한 뒤 -Apply로 가상 JSON을 적재할 수 있습니다(미실행된 선택 도구). JSON의 필드 타입과 DateOnly를 재확인합니다. Lists의 'Excel에서 새 목록 만들기'로 기존 ITAssets에 덧붙일 수 있다고 가정하지 않습니다. 새 목록을 만들었다면 내부 이름/타입/고유 제약을 스키마에 맞게 수정해야 합니다.

ITLocations에 ALL(필터 전용)과 Unknown, 샘플 위치들을 적재합니다. 기본 목록의 ID는 샘플 JSON의 임시 ID와 다르므로 실제 ID를 사용합니다.

## 3. Canvas App 생성
1. make.powerapps.com의 회사 개발 환경에서 빈 Tablet Canvas App을 생성합니다. 기존 SharePoint 폼 사용자 지정이 아닌 독립 앱을 선택합니다.
2. Settings에서 Scale to fit/Lock aspect ratio를 끄고 responsive containers를 사용합니다.
3. Data → Add data → SharePoint → 샘플 사이트 → ITAssets, ITLocations, ITAssetSummary, 필요 시 staging/events를 연결합니다. [공식 연결 방법](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/connections/connection-sharepoint-online)
4. `assets/knaufLogo.svg`를 Media로 올리고 Image 컨트롤에 연결합니다. 네비게이션과 화면/입력 컨트롤을 03_UI의 이름대로 만듭니다.
5. App.OnStart에 01, 검색에 02, 갤러리에 03, 상태 라벨에 04를 붙입니다. OnStart를 실행합니다.
6. 우선 검색·시트별 메뉴·상태 표시를 샘플 연결에서 확인합니다. 연결 없이 레이아웃만 시험하려면 11 샘플 초기화 수식을 쓰되, 이것으로 위임/보안 검증을 대체하지 않습니다.

## 4. 실제 저장 Flow 구성
1. 07의 AssetReadForEdit와 AssetWrite를 샘플 사이트 대상으로 생성합니다. Power Apps (V2) 입력 순서와 응답 키/타입을 맞춥니다.
2. 각 Flow에서 HTTP GET/IF-MATCH MERGE를 직접 시험하고, 같은 ETag로 두 번 쓰면 두 번째가 412로 거절되는지 확인합니다.
3. 앱의 Power Automate 패널에서 Flow를 추가합니다. 이름을 바꿨다면 06/07의 Run 호출도 바꿉니다.
4. 상세 컨트롤의 Default/Items/DisplayMode/OnChange를 03대로 구성하고 06·07·09·10 수식을 적용합니다. 상태 변경 사유 txtActionReason을 추가합니다.
5. 읽기 Flow의 assetJson이 ETag와 같은 버전인지 확인합니다. ID로 갤러리를 다시 읽은 값에 이전 ETag를 붙이지 않습니다.
6. 독립된 두 세션으로 동일 자산을 열고 A 저장 후 B 저장이 거절되는지 시험합니다. B 입력이 사라지면 불합격입니다.
7. S/N 동일 동시 생성·수정, 권한 없는 Flow 호출, 논리 삭제/복구 권한을 확인합니다.

## 5. 검색/집계/갱신 확장
1. 2,001개 이상 가상 레코드로 위임·검색 누락을 시험합니다. 데이터 행 한도를 1로 내려 접두어 조회도 검증합니다.
2. Summary Flow를 구현한 뒤 카드에 전체 수량/기준시각을 연결합니다. 미완료면 '-' 또는 '집계 중'을 표시합니다.
3. Timer에 05를 적용합니다. 상세 편집 중에는 새로고침하지 않고 다른 사람의 수정이 폼을 덮지 않는지 확인합니다.
4. 정밀 모드가 필요하면 AssetSearchSnapshot을 구현하고 12→08을 적용합니다. Complete=false나 응답 과대에서 전체 검색처럼 일부 결과를 표시하면 안 됩니다.
5. 내보내기는 별도 서버 Flow를 만든 뒤 연결합니다. 갤러리 AllItems가 전체 검색 결과라고 가정하지 않습니다.

## 6. 패키지 검증
이 자료의 ZIP은 앱 가져오기 파일이 아닙니다. Studio에서 만든 앱을 저장/개발 환경 게시한 후, 공식 메뉴로 msapp/패키지 또는 솔루션을 내보냅니다. 이를 다른 개발 앱/환경으로 가져와 데이터 연결·Flow·목록 ID를 재바인딩하고 전체 시험을 반복합니다. App checker가 통과한 내보내기본을 다시 열어야 합니다. 완료 판정은 06/09 문서를 따릅니다.

## 7. 실제 데이터 전환
가상 데이터 UAT를 승인한 뒤에만 실제 이관을 진행합니다. 실제 파일을 이 공개 개발 폴더/GitHub/외부 서비스에 복사하지 마세요. 실제 staging/ready 출력은 회사 내부 저장소에서 검토·적재합니다. 02의 대사·동결·롤백 절차를 적용하고 기존 Python/Excel 프로젝트는 보존합니다.

## 8. 사용자 배포
앱을 회사 그룹과 공유하고 목록 권한/Flow 실행 권한/연결 사용 권한을 별도로 점검합니다. 앱 공유만으로 데이터 권한이 자동 완성되지는 않습니다. 사용자에게 Canvas App URL 또는 Teams 접근을 제공하며 BAT/VBS는 더 이상 배포하지 않습니다. SAP는 2단계 서버 추출·대조 구현/UAT 완료 후에 활성화합니다.
