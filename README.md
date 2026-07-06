# LPR_System — 번호판 인식 주차 관리 시스템

YOLOv11m 번호판 검출 + PaddleOCR 한국어 인식 + ByteTrack 실시간 추적을 결합한
주차장 입·출차 관리 데스크톱 애플리케이션.

---

## 주요 기능

- **번호판 검출**: YOLOv11m (AIHub 부감 각도 데이터 10만 장 학습)
- **문자 인식**: PaddleOCR (한국어, CPU) + 정규식 기반 번호판 형식 교정
- **실시간 추적**: ByteTrack — 검출된 번호판을 프레임마다 추적, 화면 밖으로
  사라지면 박스 자동 소멸
- **입·출차 관리**: 화이트리스트/블랙리스트, 입출차 로그, 주차 요금 계산
- **블랙리스트 경보**: 차단 차량 인식 시 팝업 알림
- **데이터**: SQLite 저장, 엑셀 내보내기

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
| `train.py` | YOLOv11m 번호판 검출 학습 |
| `json_to_yolo.py` | AIHub JSON 라벨 → YOLO txt 변환 |
| `make_val.py` | train/val 9:1 분할 |
| `make_ocr_dataset.py` | PaddleOCR 파인튜닝 데이터셋 준비 |
| `train_ocr.py` | PaddleOCR 인식 모델 파인튜닝 |
| `dataset.yaml` | YOLO 학습 데이터 설정 |

> 대용량 데이터(`PlateSample/`, `dataset/`), 가상환경(`lpr_env/`),
> 모델 가중치(`*.pt`)는 `.gitignore`로 제외됨.

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

> ⚠️ **paddlepaddle는 반드시 CPU 버전**을 쓸 것. GPU 버전(`paddlepaddle-gpu`)은
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
