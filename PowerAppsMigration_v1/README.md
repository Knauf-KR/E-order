# Excel IT 자산 → SharePoint Lists + Power Apps Canvas 전환 설계

**상태: 실제 기존 소스·Excel을 로컬 분석한 설계/수식/가상 데이터 개발 자료. Power Apps 테넌트에서 검증된 앱 또는 가져오기 패키지가 아닙니다.**

기존 `ITAssetManager` v0.5 파일과 회사 Excel은 수정하지 않았습니다. 이 폴더는 별도 전환 프로젝트입니다. 실제 자산 행, S/N, 사용자·계정·재무 정보, 실제 SAP 결과를 포함하지 않습니다. `sample/`은 `DEMO-*` 가상 데이터만 사용합니다. 실제 파일 분석 결과와 실제 이관 출력은 별도 비공개 로컬 폴더에 보관했습니다.

| 요청 결과물 | 파일 |
|---|---|
| 실제 코드/데이터 구조 분석 | [01 기존 구조 분석](docs/01_source_analysis.md) |
| Lists 구조·이관 계획 | [02 데이터 모델·이관](docs/02_lists_and_migration.md), [전체 열 정의 JSON](schema/sharepoint-lists.json) |
| 화면별 UI 설계 | [03 UI 설계](docs/03_ui.md), [가상 데이터 UI 시안](prototype/index.html) |
| 검색·필터·상세 Power Fx | [04 수식 적용표](docs/04_powerfx.md), `powerfx/*.fx` |
| 기능 대응표 | [05 기능 대응](docs/05_feature_mapping.md) |
| 공식 소스 형식·패키지 검토 | [06 공식 소스와 패키지](docs/06_source_format_and_packaging.md) |
| 실제 적용 절차 | [08 적용 가이드](docs/08_apply_guide.md) |
| 저장·충돌·권한·정밀검색·SAP 구현 계약 | [07 서버 흐름 계약](docs/07_flow_contracts.md) |
| 검증/공식 근거 | [09 검증 계획](docs/09_validation.md), [공식 참고 문서](docs/10_references.md) |

## 먼저 볼 핵심 결정
- 다섯 Excel 자산 시트를 **ITAssets 하나**로 합칩니다. Office/Shared/Plant 사용 구분과 InUse/Stock/Retired 상태를 분리합니다.
- SerialKey에 SharePoint 고유 제약을 적용합니다. 기존 중복은 staging에서 전부 보존하고 검토한 후 승격합니다.
- 대량 목록은 접두어 검색을 사용합니다. 기존의 모든 열·복수 단어·부분 문자열 검색은 **완전성이 확인된 소규모 스냅샷 모드**로 별도 제공합니다. 모든 행이 검색되는 것처럼 잘린 컬렉션을 표시하지 않습니다.
- 저장은 적용 버튼 한 번으로 SharePoint 항목에 반영합니다. 동시 편집은 읽을 때 받은 ETag와 쓰기 시 IF-MATCH로 보호합니다. 단순 Modified 사전 비교나 클라이언트 중복 검사만으로 보호된다고 가정하지 않습니다.
- 기존 OS 팝업은 Canvas 내부 모달로 재현합니다. 30초 갱신은 푸시 실시간이 아니며 편집 중에는 멈춥니다.
- `.pa.yaml` 예시와 ZIP을 곧바로 Canvas 앱으로 가져올 수 있다고 주장하지 않습니다. Studio에서 샘플 앱을 만들고 저장·재열기·테스트·공식 내보내기하는 경로가 기본입니다.

## 로컬 실행 예제
```powershell
python -m pip install openpyxl
python tools/make_samples.py
python -m unittest discover -s tools -p 'test_*.py' -v
# 실제 데이터 변환은 반드시 배포 폴더 밖의 회사 로컬 경로로 출력
python tools/convert_excel.py --input "C:\CompanyLocal\IT_자산리스트.xlsx" --output "C:\CompanyLocal\migration-review"
# Lists 스키마는 기본 dry-run. 실제 테넌트 작업은 수행하지 않았습니다.
pwsh tools/provision-lists.ps1
```

Python 개발 데이터 생성과 변환은 로컬 파일 작업입니다. `--sample`은 가상 파일에만 사용하세요. 로컬 HTML은 Power Apps가 아닌 화면 시안이며 브라우저에서 파일을 열어 시험할 수 있습니다.

## UI 시안 시험
파일 직접 열기가 브라우저 정책으로 차단되면 이 폴더에서 아래 서버를 실행하고 `http://127.0.0.1:8877/prototype/`을 여세요. 서버는 가상 데이터 개발 폴더만 로컬에 제공합니다.
```powershell
python -m http.server 8877 --bind 127.0.0.1
# 선택: requirements-dev와 Playwright 브라우저를 준비한 뒤
python tools/verify_prototype.py --url http://127.0.0.1:8877/prototype/index.html
```
