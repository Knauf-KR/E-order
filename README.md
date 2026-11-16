# Knauf IT 자산 관리 v0.5 — 공유 폴더 배치

`launch.vbs`, `launch.bat`과 `ITAssetManager` 폴더를 기존 `IT_자산리스트.xlsx` 옆에 복사하세요.

```text
OneDrive 공유 폴더/
├─ IT_자산리스트.xlsx
├─ launch.vbs  ← 평소 실행용 (콘솔 창 없음)
├─ launch.bat  ← 설치 처리 및 문제 확인용
└─ ITAssetManager/
```

**launch.vbs를 더블클릭하면 콘솔 창 없이 프로그램만 열립니다.** 첫 실행 시 설치 확인도 숨겨서 처리하며, 처음 준비할 때 짧은 안내창이 뜰 수 있습니다. 실행 위치의 Excel을 자동으로 엽니다. 각자 OneDrive의 앞쪽 경로가 달라도 됩니다. 예전 PC별 절대 경로 설정은 시작 시 사용하지 않습니다.

Python 3.11 이상(Python Launcher, pip, Tcl/Tk 포함)이 필요합니다. 최초 실행 시 설치되는 Python 패키지는 각 PC의 LOCALAPPDATA에 보관되며 공유 폴더에 가상환경을 만들지 않습니다.

공유 Excel과 프로그램 폴더는 OneDrive에서 '이 장치에 항상 유지'로 설정하세요. 회사 Excel 파일을 새 파일로 교체하지 말고 그대로 두세요.

자동 저장·외부 변경 반영은 유지됩니다. OneDrive가 각 PC에 동기화한 뒤 자동 갱신하므로 수정자는 한 번에 한 사람으로 운영하세요.

[자세한 사용 안내](ITAssetManager/README.md)

BAT을 직접 더블클릭하면 Windows 특성상 콘솔 창이 잠깐 생길 수 있습니다. 창 없이 시작하려면 launch.vbs를 사용하세요. 회사 정책으로 Windows Script Host/VBScript가 차단된 PC는 IT 담당자의 확인이 필요합니다.
