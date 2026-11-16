# Knauf IT 자산 관리 v0.4 — 공유 폴더 배치

`launch.bat`과 `ITAssetManager` 폴더를 기존 `IT_자산리스트.xlsx` 옆에 복사하세요.

```text
OneDrive 공유 폴더/
├─ IT_자산리스트.xlsx
├─ launch.bat
└─ ITAssetManager/
```

**launch.bat을 더블클릭하면 같은 위치의 Excel을 자동으로 엽니다.** 각자 OneDrive의 앞쪽 경로가 달라도 됩니다. 예전 PC별 절대 경로 설정은 시작 시 사용하지 않습니다.

Python 3.11 이상(Python Launcher, pip, Tcl/Tk 포함)이 필요합니다. 최초 실행 시 설치되는 Python 패키지는 각 PC의 LOCALAPPDATA에 보관되며 공유 폴더에 가상환경을 만들지 않습니다.

공유 Excel과 프로그램 폴더는 OneDrive에서 '이 장치에 항상 유지'로 설정하세요. 회사 Excel 파일을 새 파일로 교체하지 말고 그대로 두세요.

자동 저장·외부 변경 반영은 유지됩니다. OneDrive가 각 PC에 동기화한 뒤 자동 갱신하므로 수정자는 한 번에 한 사람으로 운영하세요.

[자세한 사용 안내](ITAssetManager/README.md)
