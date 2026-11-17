# 6. Microsoft 공식 소스 형식과 패키지 생성 검토

확인일: 2026-11-17. 테넌트/Studio 버전에 따라 메뉴와 지원 범위는 달라질 수 있습니다.

## 공식 형식의 구분
현재 공식 소스는 `.pa.yaml`이며, App/Screens/ComponentDefinitions 같은 최상위 노드와 Control@버전, '='로 시작하는 수식을 사용합니다. Studio가 생성한 msapp의 Src에서 확인할 수 있습니다. 이 YAML만 바꿔 다시 ZIP으로 묶는 방식은 공식 가져오기 패키지를 생성하는 경로가 아닙니다. 추출된 YAML은 기본적으로 검토용이고 외부 수정 반영은 지원되는 Git Integration 경로를 사용해야 합니다. [Microsoft 소스 형식](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/power-apps-yaml)

컨트롤 Code view의 복사/붙여넣기는 Studio가 생성한 코드를 기준으로 사용합니다. 앱 전체나 데이터 연결을 포함한 배포를 대체하지 않습니다. 이 자료의 Power Fx는 우선 속성 창에서 적용합니다. [Code view](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/code-view)

## 이번 자료의 정확한 상태
- `reference/format-example.pa.yaml`: 공식 v3 JSON Schema에 대해 **구조 검사만 한 최소 예시**입니다. Studio export가 아니고, Control 속성/버전·Power Fx·데이터 연결을 실행 검증하지 않았습니다.
- `powerfx/*.fx`: 컨트롤 속성에 적용하는 수식 초안입니다. Power Fx/Studio 컴파일 완료 파일이 아닙니다.
- `schema/sharepoint-lists.json`: Lists 생성 계약입니다. Microsoft Canvas 앱 소스나 Flow 패키지 형식이 아닙니다.
- `prototype/index.html`: UX 시안입니다. Canvas 런타임이 아닙니다.
- 이 폴더/다운로드 ZIP은 **설계·개발 자료 묶음**입니다. Power Apps 'Import canvas app'에 업로드하지 않습니다. `.msapp`나 솔루션 ZIP을 위조해 넣지 않았습니다.

## 권장 구현 경로
1. 회사 개발 환경에서 빈 Tablet Canvas App을 실제 생성합니다.
2. 가상 Lists 연결, 컨테이너·컨트롤 생성, 이 자료의 수식 적용, Flow 추가를 Studio에서 수행합니다.
3. 앱 검사·위임·권한·동시 편집·접근성 시험 후 개발 환경에 저장/게시합니다.
4. Studio가 생성한 `.msapp`를 공식 메뉴로 내려받고, 새 개발 앱으로 다시 열어 검증합니다.
5. 가능하면 솔루션에 앱/Flow/연결 참조/환경 변수를 넣어 ALM을 구성합니다. 솔루션은 SharePoint 목록 자체와 항목 데이터를 자동 이관하지 않으므로 별도 생성·검증합니다.
6. 지원되는 Power Platform Git Integration으로 소스를 관리합니다. 대규모 YAML 수기 생성보다 Studio가 생성한 소스를 기준으로 최소 변경·개발 환경 검증을 합니다. [Git Integration](https://learn.microsoft.com/en-us/power-platform/alm/git-integration/canvas-apps-git-integration)

## 실제로 유효한 패키지를 만드는 조건
**단일 msapp:** Studio에서 생성·저장한 실제 앱을 내려받은 후 공식 '열기/가져오기'로 새 앱에서 재확인합니다. 이때 SharePoint 데이터/연결 권한이 같이 생긴다고 가정하지 않습니다. [단일 앱 파일](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/export-import-single-app)

**Canvas 앱 패키지 ZIP:** Maker의 Export Package에서 생성하고, 대상의 Import Canvas App에서 리소스를 새로 생성/연결하여 시험합니다. 이 개발 자료 ZIP과 다릅니다. ALM이 필요하면 솔루션 경로를 우선합니다. [앱 패키지](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/export-import-app-package)

**솔루션:** 실제 앱·Flow가 있는 환경에서 export하고 별도 개발 환경에 import한 뒤 연결 참조/사이트·목록 바인딩/실행 계정을 재설정해 시험합니다. SharePoint 목록 ID가 환경마다 달라지는 점을 확인합니다.

## PAC 명령 검토 — 기본 배포 경로가 아님
Microsoft CLI 문서에 canvas pack/unpack은 deprecated로 표시됩니다. 이전 `.fx.yaml` 방식으로 새 자료를 만든 다음 곧바로 pack하면 된다고 안내하지 않습니다. 문서에 SourceCode layout 옵션이 있으나 실제 export 시드와 CLI 버전·Studio 재열기 검증이 필요합니다. [공식 CLI](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/canvas)

인증한 개발 환경에 실제 앱이 생긴 이후에만 아래와 같은 조회/다운로드를 사용할 수 있습니다. 여기서는 실행하지 않았습니다.
```powershell
pac --version
pac canvas list
pac canvas download --name "<실제 개발 앱 ID>" --file-name "KnaufITAssets.msapp" --extract-to-directory "exported-app"
```

pack/unpack 실험이 꼭 필요하면 검증된 실제 export의 **무수정 round-trip**부터 별도 복사본에서 하고, Studio 재열기·App checker·재저장·새 환경 가져오기를 모두 통과해야 합니다. CLI가 파일을 생성하거나 JSON Schema 검사가 통과했다는 사실만으로 '유효하고 가져오기 가능한 Canvas App'이라고 판정하지 않습니다.
