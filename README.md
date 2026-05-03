# Fuck NFD (Mac 한글 파일명 자소 분리 해결 프로그램)

## 📝 프로젝트 소개

이 프로그램은 macOS 환경에서 생성된 파일이나 폴더를 Windows 등 다른 운영체제로 이동할 때 발생하는 **'한글 파일명 자소 분리(NFD)' 현상**을 해결하기 위해 제작된 간편한 GUI 유틸리티입니다. 직관적인 드래그 앤 드롭 인터페이스를 통해 깨진 파일명을 원래의 정상적인 형태(NFC)로 손쉽게 일괄 변환합니다.

## ✨ 주요 기능

- **자소 분리 파일명 복구**: NFD(Normalization Form Canonical Decomposition)로 강제 분리된 한글 파일명을 표준 NFC(Normalization Form Canonical Composition) 형식으로 자동 병합합니다.
- **드래그 앤 드롭 (Drag & Drop) 지원**: `tkinterdnd2` 패키지를 활용하여, 변환이 필요한 파일이나 폴더를 프로그램 창에 끌어다 놓기만 하면 즉시 작동합니다[cite: 1].
- **독립 실행 파일 제공**: 포함된 `build.bat`을 통해 파이썬이 설치되지 않은 환경에서도 실행 가능한 `.exe` 파일로 쉽게 빌드할 수 있습니다[cite: 1].

## 📂 파일 구성

- `fuck_nfd.py`: 프로그램의 메인 파이썬 스크립트입니다[cite: 1].
- `requirements.txt`: 프로그램 실행 및 빌드에 필요한 외부 라이브러리 목록이 포함되어 있습니다 (`tkinterdnd2>=0.4.2`)[cite: 1].
- `build.bat`: Windows 환경에서 PyInstaller 등을 이용해 실행 파일로 패키징하는 배치 스크립트입니다[cite: 1].
- `fucknfd.ico` & `fucknfd.png`: 프로그램 UI 및 실행 파일에 사용되는 아이콘 이미지 리소스입니다[cite: 1].
- `LICENSE`: 프로젝트 라이선스 정보입니다[cite: 1].

## 🚀 설치 및 사용 방법

### 소스 코드로 직접 실행할 경우 (개발자용)

1. Python 3.x 환경이 설치되어 있어야 합니다.
2. 저장소를 클론하거나 다운로드한 후, 터미널에서 필수 패키지를 설치합니다.

   ```bash
   pip install -r requirements.txt
   ```

3. 메인 스크립트를 실행합니다.
   ```bash
   python fuck_nfd.py
   ```

### 실행 파일(.exe)로 사용할 경우 (일반 사용자용)

1. `build.bat` 파일을 더블 클릭하여 실행 파일을 빌드합니다[cite: 1].
2. 생성된 `fuck_nfd.exe` 파일을 실행합니다.
3. 자소가 분리된 파일이나 폴더를 열려있는 프로그램 창으로 드래그 앤 드롭하여 변환합니다.
