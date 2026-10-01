# HANDOFF — 포트폴리오 작업 컨텍스트

이 세션 compact 직전에 남기는 핸드오프 문서. 다음 세션(또는 compact 이후)에서
이어서 작업할 때 참고할 것. 사람보다는 AI가 맥락 파악용으로 읽는 용도.

---

## 지금 하고 있는 것: 포트폴리오 정리

사용자(지수, seo941024)는 **데이터 분석/SQL** 직무로 취업 준비 중. GitHub
프로필(`seo941024/seo941024`)과 각 프로젝트 레포를 포트폴리오로 다듬는 작업을
진행해왔음.

### 포트폴리오 소개 구조 (확정)

사용자가 직접 정리한 4개 카테고리 (최종 확정 표):

| # | 카테고리 | 핵심 역량 | 예시 |
|---|---|---|---|
| 1 | 웹 구현 | 프론트엔드/웹페이지 작업 | Web-PRG(HTML/CSS), Home-test 안 todolist/petcare 등 |
| 2 | 데이터 수집·게임·웹서비스 | 외부 API 연동 + 자동화 파이프라인 | `byeolnim.app` (넥슨 API, Vercel Cron, Redis) |
| 3 | 주차장 관리 시스템(Qt) | 컴퓨터비전 + OCR + SQL 분석 | `LPR_System` |
| 4 | 기본기+과거 프로젝트 | 학습 과정, 코스웍 | Python(가챠 시뮬레이터), Java, Cpp-CV 등 |

**카테고리 2 (byeolnim.app) 상세**: 메이플스토리 계산기. 넥슨 공식 API →
Vercel 서버리스 함수로 프록시(CORS 우회) → Vercel Cron으로 매일 자동 배치 →
Redis에 스냅샷 적재(캐릭터 성장 추적, 최대 180개 롤링 버퍼) → 유저에게
성장 그래프로 시각화. 소울/스타포스/큐브 시뮬레이터는 실제 게임 확률
테이블을 1차 소스(공식 패치노트, 나무위키 원문)와 대조 검증해서 구현.
**⚠ 이 프로젝트는 아직 GitHub 레포 목록(13개)에 없음 — 별도로 올릴지
확인 필요.**

**카테고리 3 (LPR_System) 상세**: 이 세션에서 가장 많이 작업한 메인
프로젝트. 아래 "LPR_System 현황" 참고.

**카테고리 4 상세**: Python(가챠 Monte Carlo 시뮬레이터), Java,
Cpp-CV(C/OpenCV 실습) 등 코스웍성 레포.

---

## LPR_System 현황 (가장 공들인 프로젝트)

- **경로**: `C:\Users\AISW_203_106\Desktop\2601340028\Personal_Projoect\LPR_Parking`
  (세션 중 `Desktop\LPR_Parking`에서 이 경로로 이동했음 — 과거 메시지에
  옛 경로 언급 있으면 무시할 것)
- **GitHub**: https://github.com/seo941024/LPR_System
- **스택**: YOLOv11m(검출, PyTorch) + ByteTrack(추적) + PaddleOCR(한국어
  인식, CPU 전용) + PyQt6(데스크톱 앱) + SQLite + SQL(윈도우함수/CTE) +
  Streamlit + Plotly
- **학습 결과**: AIHub 10만 장, 100에폭, mAP@0.5 = 0.9305, mAP@0.5:0.95 = 0.8619
  (전체 에폭별 수치는 로컬 `runs/plate_detect-6/results.csv`에 있음,
  `.gitignore`로 커밋 안 됨. 그래프 요약본은 `보고서_그래프/`에 커밋됨)
- **중요 기술 결정 (README에 이미 기록됨)**:
  - EasyOCR → PaddleOCR 전환 (한국어 인식 정확도 때문)
  - YOLO(torch-GPU) + PaddleOCR(paddle-GPU) CUDA 심볼 충돌 → OCR을
    **CPU 전용 paddle**로 분리
  - 학습 데이터(부감 각도)와 실배포 환경 도메인 갭 실측 검증
- **analytics/ 폴더**: SQL 분석 + Streamlit 대시보드. 별도 가상환경
  `analytics/dash_env` 사용 (protobuf 버전 충돌로 `lpr_system`과 격리).
  `demo_parking.db`는 합성 데이터(4주, 방문 1,094건).
  `lpr_system/load_demo_data.py`로 이 데모 데이터를 실제 앱 DB(`parking.db`)에
  불러올 수 있음 — 대시보드/통계 화면 스크린샷 찍을 때 사용.
- **데이터 도구 탐색**: 같은 LPR 데이터셋을 SQLite(DB Browser), Power Query,
  Power BI, Databricks(PySpark/Spark SQL)로도 다뤄봄. 현재 `analytics/README.md`의
  "데이터 도구 탐색" 섹션에 텍스트만 있고 이미지는 없음(사용자가 직접 찍은
  스크린샷으로 교체 예정이라 이전에 넣었던 임시 이미지는 삭제함).
  **⚠ 추가 확인 필요**: 사용자가 **Azure Blob Storage**에 데이터 올려서
  Power BI·Databricks 양쪽에서 연결해 썼다고 함 — 이거 analytics/README.md에
  아직 반영 안 됨. "데이터 도구 탐색" 섹션에 Blob Storage 항목 추가할 것.
- **메인 README 상단**: 실제 앱 스크린샷(`assets/app_screenshot.png`,
  영상 파일 처리 화면) 넣어둠.
- **이모지**: 저장소 전체에서 진짜 이모지(🚗🅿️★✅❌🚫🗑⚠️) 다 제거함.
  화살표(→↓↑↔)는 다이어그램 표기라 의도적으로 남김.

---

## GitHub 레포 정리 현황 (13개 중)

| 레포 | 상태 |
|---|---|
| LPR_System | 위 참고, 충실 |
| seo941024 (프로필) | LPR_System 대표 프로젝트로 교체 완료, 이모지 제거 완료 |
| DeskPoseAI | README 충실, 안 건드림 |
| EntranceCounter | README 충실, 안 건드림 |
| PromptScene | README 충실, 안 건드림. **데이터 쪽으로 보완 가능**(검색 로그를
  SQLite 테이블화, 프롬프트 실험 추적 테이블화 — 사용자에게 제안했고 아직 실행 안 함) |
| waste-lens | README 충실, 안 건드림. **데이터 쪽으로 보완 가능**
  (disposal_rules.json → SQLite, 추론 로그 테이블화 — 제안만 하고 실행 안 함) |
| Python | README 있음(가챠 시뮬레이터), 안 건드림 |
| **Home-test** | **README 완전히 비어있음 — 수정 필요, 아직 안 함** |
| **Java** | **README가 플레이스홀더 템플릿 그대로 — 수정 필요, 아직 안 함** |
| **Web-PRG** | **README가 BLT 샌드위치 설명만 있는데 실제론 petcare/todolist/web/web_practice
  등 여러 하위 프로젝트 있음 — 수정 필요, 아직 안 함** |
| Cpp-CV | README **아예 없음**. 사용자가 "README 없는 건 하지마"라고 해서
  **건드리지 않기로 확정** |
| ParkingSystem | LPR_System의 구버전(EasyOCR 시절) 중복 레포로 추정.
  사용자에게 언급만 했고 처리 방향 안 정함 (아카이브/삭제/방치 중 결정 필요) |

---

## 다음에 할 일 (우선순위)

1. **Azure Blob Storage** 내용을 `analytics/README.md` "데이터 도구 탐색"에 추가
2. 사용자가 대시보드/앱 스크린샷을 직접 찍으면 `analytics/README.md`,
   `LPR_System/README.md`에 반영
3. `Home-test`, `Java`, `Web-PRG` 레포 README 보완 (README 자체가 없는
   `Cpp-CV`는 건드리지 말 것)
4. 포트폴리오 소개 문서를 4-파트 구조로 실제 작성 (아직 작성 안 함,
   구조만 확정됨)
5. `byeolnim.app`을 GitHub에 올릴지 사용자에게 확인
6. (선택) PromptScene, waste-lens에 SQL/DB 레이어 보완 — 제안만 한 상태

---

## 작업 환경 메모

- 로컬 git 저장소 2개를 다루는 중:
  - `LPR_Parking` (= LPR_System 레포) — 현재 작업 디렉토리
  - 프로필 레포(`seo941024/seo941024`)는 스크래치 디렉토리에 따로 클론해서 작업함
    (`...\scratchpad\profile_readme\`) — 세션 재시작하면 다시 클론해야 할 수 있음
- `lpr_env`(메인 앱)와 `analytics/dash_env`(대시보드)는 **반드시 분리 유지** —
  paddlepaddle(GPU 금지, CPU만)과 streamlit의 protobuf 버전이 충돌함
- 과거 폴더 이동(`Desktop\LPR_Parking` → `Desktop\2601340028\Personal_Projoect\LPR_Parking`)
  때문에 `lpr_env`의 activate 스크립트가 한때 깨졌었음 — 지금은 `venv --upgrade`
  + 경로 치환으로 복구 완료된 상태
