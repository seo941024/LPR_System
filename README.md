# LPR_System — 번호판 인식 주차 관리 시스템

YOLOv11m 번호판 검출 + PaddleOCR 한국어 인식 + ByteTrack 실시간 추적을 결합한
주차장 입·출차 관리 데스크톱 애플리케이션.

<img src="https://raw.githubusercontent.com/seo941024/LPR_System/master/assets/app_screenshot.png" width="800">

---

## 프로젝트 하이라이트

**한 줄 요약**
YOLOv11m 객체 검출 + PaddleOCR 문자 인식 + ByteTrack 실시간 추적을 결합해 주차장 입출차를 자동 관리하고, 축적된 로그를 SQL로 분석해 대시보드로 시각화하는 End-to-End 프로젝트.

**기술 스택**
`Python · PyTorch · YOLOv11 · PaddleOCR · ByteTrack · PyQt6 · SQLite · SQL(Window Function/CTE) · Streamlit · Plotly`

**핵심 기능**
- AIHub 데이터 10만 장으로 YOLOv11m 번호판 검출 모델 직접 학습 (mAP@0.5 0.931, mAP@0.5:0.95 0.862)
- ByteTrack으로 검출 객체를 실시간 추적, GPU(검출)/CPU(OCR) 파이프라인 분리로 프레임 끊김 없이 처리
- PaddleOCR 기반 한국어 번호판 인식 + 정규식 형식 교정, 화이트/블랙리스트 관리, 요금 자동 계산
- 입출차 로그를 SQL(LAG 윈도우 함수, CTE)로 분석해 방문 추이·피크타임·매출·재방문 패턴을 Streamlit 대시보드로 시각화

**기술적 문제 해결 경험**
- YOLO(torch-GPU)와 PaddleOCR(paddle-GPU)가 같은 프로세스에서 CUDA 심볼 충돌 → OCR을 CPU 전용으로 분리해 안정적 공존 구조 설계
- 학습 데이터(부감 각도)와 실제 배포 환경(정면/저조도) 간 도메인 불일치를 실측 검증으로 규명, 원인을 "성능 저하"가 아닌 "도메인 갭"으로 정확히 진단
- 검출·인식 로직과 SQL 분석 대시보드의 의존성 충돌(protobuf 버전)을 발견해 별도 가상환경으로 격리, 기존 앱에 영향 없이 기능 확장

**성과 수치**
- YOLOv11m mAP@0.5 93.1% (자체 도메인 검증 기준)
- 합성 4주 데이터 기준 입출차 1,094건 분석, SQL 쿼리 7종 (윈도우 함수/CTE 활용)

---

## 주요 기능

- **번호판 검출**: YOLOv11m (AIHub 부감 각도 데이터 10만 장 학습)
- **문자 인식**: PaddleOCR (한국어, CPU) + 정규식 기반 번호판 형식 교정
- **실시간 추적**: ByteTrack — 검출된 번호판을 프레임마다 추적, 화면 밖으로
  사라지면 박스 자동 소멸
- **입·출차 관리**: 화이트리스트/블랙리스트, 입출차 로그, 주차 요금 계산
- **블랙리스트 경보**: 차단 차량 인식 시 팝업 알림
- **데이터**: SQLite 저장, 엑셀 내보내기
- **데이터 분석 대시보드**: 입출차 로그를 SQL(윈도우 함수·CTE)로 분석해
  방문 추이·피크타임·매출·재방문 패턴을 Streamlit으로 시각화 (`analytics/`)

---

## 아키텍처

```
영상/카메라 프레임
   │
   ├─ YOLOv11m track (GPU)  ──►  실시간 박스 (매 프레임 추적)
   │
   └─ track ID별 crop  ──►  PaddleOCR (CPU)  ──►  번호판 텍스트
                                                    │
                                          투표·중복제거·스냅보정
                                                    │
                                          SQLite (로그 / 입출차 / 요금)
```

- **검출·추적(GPU)과 OCR(CPU)을 분리** — OCR이 프레임 루프를 막지 않아 영상이 부드러움
- 송출 화면은 960px로 축소해 렌더링 부하 감소

---

## 폴더 구성

| 경로 | 설명 |
|------|------|
| `lpr_system/` | 데스크톱 앱 (PyQt6) 및 파이프라인 |
| `analytics/` | 입출차 로그 SQL 분석 + Streamlit 대시보드 (독립 가상환경) |
| `train.py` | YOLOv11m 번호판 검출 학습 |
| `json_to_yolo.py` | AIHub JSON 라벨 → YOLO txt 변환 |
| `make_val.py` | train/val 9:1 분할 |
| `make_ocr_dataset.py` | PaddleOCR 파인튜닝 데이터셋 준비 |
| `train_ocr.py` | PaddleOCR 인식 모델 파인튜닝 |
| `dataset.yaml` | YOLO 학습 데이터 설정 |

> 대용량 원본 데이터(`PlateSample/`, `dataset/`), 가상환경(`lpr_env/`,
> `analytics/dash_env/`)은 `.gitignore`로 제외됨. 단, 앱 실행에 필요한
> 배포용 모델(`lpr_system/models/plate_yolo11m.pt`, 38MB)은 예외로 커밋에 포함.

---

## 설치

```bash
pip install -r lpr_system/requirements.txt
```

주요 의존성:
- PyQt6, qtawesome (UI)
- ultralytics, torch (YOLOv11m 검출 · GPU)
- paddleocr==2.7.3, **paddlepaddle==2.6.2 (CPU 전용)** (OCR)
- opencv-python==4.6.0.66, numpy==1.26.4

> **paddlepaddle는 반드시 CPU 버전**을 쓸 것. GPU 버전(`paddlepaddle-gpu`)은
> import 시 CUDA 심볼을 등록해 torch(YOLO)-GPU와 충돌한다. OCR은 번호판 crop만
> 처리하므로 CPU로도 충분히 빠르다.

---

## 실행

```bash
cd lpr_system
python app_pyqt6.py
```

앱에서 영상 파일 또는 웹캠/RTSP 카메라를 선택해 실시간 인식.

---

## 데이터 분석 대시보드

```bash
cd analytics
python -m venv dash_env
dash_env\Scripts\pip install -r requirements.txt
dash_env\Scripts\python -m streamlit run dashboard.py
```

> `lpr_system`(`lpr_env`)과 완전히 분리된 독립 가상환경. streamlit이 요구하는
> 최신 protobuf가 paddlepaddle(`<=3.20.2` 고정)과 충돌해 메인 앱과 격리했다.
> 실 카메라 배포 전이라 `demo_parking.db`는 합성 데이터 — 자세한 내용은
> [`analytics/README.md`](analytics/README.md) 참고.

---

## 학습 (재학습 시)

```bash
# 1) AIHub JSON → YOLO 라벨 변환
python json_to_yolo.py
# 2) train/val 분할
python make_val.py
# 3) YOLOv11m 학습
python train.py
```

학습 결과 `runs/plate_detect/weights/best.pt` 를 `lpr_system/models/` 로
복사해 사용.

---

## 중요 노트 (도메인 주의)

번호판 검출 모델은 **학습한 카메라 각도**에서만 잘 작동한다.

- 현재 `plate_yolo11m.pt` 는 **부감(overhead, 위에서 내려다보는) 각도** 데이터로
  학습됨 → 부감 CCTV 영상에서 검출률 높음 (val 이미지 15/15, 실측 영상 95%)
- **정면(eye-level) 영상에서는 검출되지 않음** — 성능 문제가 아니라 도메인 불일치.
  정면 배포가 필요하면 정면 데이터로 별도 학습 필요.

실제 주차장 입구 CCTV는 통상 부감 각도이므로 현재 모델로 배포 가능.
