"""
detector.py — 번호판 검출 · 색상 분류 · 전처리 모듈
YOLO(번호판 검출) + HSV 폴백 이중 검출
"""
 
import os
import threading
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict

# ── YOLO 모델 ────────────────────────────────────────────────────
# YOLOv11m, AIHub 부감(overhead) 각도 데이터 10만장 학습.
# 실제 배포 카메라도 부감 각도이므로 이 모델을 사용한다.
_MODELS_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
_YOLO_PT     = os.path.join(_MODELS_DIR, "plate_yolo11m.pt")
_YOLO_MODEL  = None
_YOLO_CONF   = 0.07   # recall 최우선 (낮출수록 더 많이 잡음, 오탐은 OCR이 걸러냄)
_YOLO_LOCK   = threading.Lock()
try:
    import torch as _torch
    _YOLO_DEVICE = "cuda" if _torch.cuda.is_available() else "cpu"
except ImportError:
    _YOLO_DEVICE = "cpu"
 
 
def _load_yolo():
    global _YOLO_MODEL
    try:
        from ultralytics import YOLO
        model = YOLO(_YOLO_PT)
        model(np.zeros((64, 64, 3), dtype=np.uint8), verbose=False, device=_YOLO_DEVICE)
        with _YOLO_LOCK:
            _YOLO_MODEL = model
        print(f"[Detector] YOLO 로드 완료: {_YOLO_PT} ({_YOLO_DEVICE.upper()})")
    except Exception as e:
        print(f"[Detector] YOLO 로드 실패 (HSV 폴백 사용): {e}")
 
 
threading.Thread(target=_load_yolo, daemon=True).start()
 
# ── 상수 ──────────────────────────────────────────────────────
HSV_RANGES = {
    "WHITE":       (np.array([0,   0, 130], np.uint8), np.array([180, 60, 255], np.uint8)),
    "GREENYELLOW": (np.array([35,  60,  40], np.uint8), np.array([90, 255, 220], np.uint8)),
    "YELLOW":      (np.array([18,  80, 120], np.uint8), np.array([35, 255, 255], np.uint8)),
    "BLUE":        (np.array([95,  80,  50], np.uint8), np.array([135, 255, 255], np.uint8)),
    "LIGHTBLUE":   (np.array([90,  30,  80], np.uint8), np.array([130, 100, 255], np.uint8)),
    "ORANGE":      (np.array([8,  100, 100], np.uint8), np.array([18, 255, 255], np.uint8)),
}
PLATE_TYPE_MAP = {
    "WHITE": "NEW", "GREENYELLOW": "OLD", "YELLOW": "NEW", "BLUE": "NEW",
    "LIGHTBLUE": "NEW", "ORANGE": "NEW",
}
 
# ▼ 임계값 완화: 실제 번호판 미검출 방지 ▼
MIN_AREA      = 700    # 멀리 있는 작은 번호판까지 포착
MAX_AREA      = 45000
MIN_ASPECT    = 1.1    # 비스듬히 찍힌 번호판 허용
MAX_ASPECT    = 9.0
MIN_SOLID     = 0.35   # 번호판 recall 최우선
NMS_IOU_TH    = 0.3
MIN_PLATE_W_FRAC = 0.02  # 극소 번호판까지 허용
NORM_WIDTH    = 320
NORM_HEIGHT   = 80
MIN_FRAME_DIM = 64
 
# CLAHE: 스레드별 독립 인스턴스 (레이스 컨디션 방지)
_local = threading.local()
 
 
def _get_clahe() -> cv2.CLAHE:
    if not hasattr(_local, "clahe"):
        _local.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return _local.clahe
 
 
# ── OpenCV CUDA 사용 가능 여부 자동 감지 ───────────────────────
try:
    _CUDA_CV = cv2.cuda.getCudaEnabledDeviceCount() > 0
except Exception:
    _CUDA_CV = False
 
# ── 카메라별 BackgroundSubtractor ─────────────────────────────
_bg_subtractors: Dict[str, object] = {}
_bg_lock = threading.Lock()
 
 
def get_bg_subtractor(camera_id: str = "default") -> object:
    with _bg_lock:
        if camera_id not in _bg_subtractors:
            if _CUDA_CV:
                try:
                    bgs = cv2.cuda.createBackgroundSubtractorMOG2(
                        history=100, varThreshold=25, detectShadows=False
                    )
                except Exception:
                    bgs = cv2.createBackgroundSubtractorMOG2(
                        history=100, varThreshold=25, detectShadows=False
                    )
            else:
                bgs = cv2.createBackgroundSubtractorMOG2(
                    history=100, varThreshold=25, detectShadows=False
                )
            _bg_subtractors[camera_id] = bgs
        return _bg_subtractors[camera_id]
 
 
def has_motion(frame: np.ndarray, min_pixels: int = 80,
               camera_id: str = "default") -> bool:
    """
    느린 차·정지 차도 놓치지 않도록 임계값을 낮게 유지.
    MOG2가 느린 차를 배경으로 학습하는 문제를 막기 위해
    learningRate를 0으로 고정(배경 갱신 안 함).
    """
    if frame is None or frame.size == 0:
        return False
    bgs = get_bg_subtractor(camera_id)
    if _CUDA_CV and hasattr(bgs, "apply") and "cuda" in type(bgs).__module__:
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(frame)
        gpu_fg = bgs.apply(gpu_frame, learningRate=0)
        fg = gpu_fg.download()
    else:
        fg = bgs.apply(frame, learningRate=0)
    return int(cv2.countNonZero(fg)) >= min_pixels
 
 
def release_bg_subtractor(camera_id: str) -> None:
    with _bg_lock:
        _bg_subtractors.pop(camera_id, None)
 
 
# ── NMS ───────────────────────────────────────────────────────
 
def _iou(a: Tuple, b: Tuple) -> float:
    ax1, ay1 = a[0], a[1]
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx1, by1 = b[0], b[1]
    bx2, by2 = b[0] + b[2], b[1] + b[3]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0
 
 
def _nms(candidates: list, iou_threshold: float = NMS_IOU_TH) -> list:
    if not candidates:
        return []
    sorted_c = sorted(candidates, key=lambda x: x[1][2] * x[1][3], reverse=True)
    kept = []
    for cand in sorted_c:
        if all(_iou(cand[1], k[1]) < iou_threshold for k in kept):
            kept.append(cand)
    return kept
 
 
# ── 도로 표지판 제거 ────────────────────────────────────────────
 
def _is_road_sign(roi: np.ndarray) -> bool:
    """파란 배경이 55% 이상이면 도로 표지판으로 간주."""
    if roi is None or roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsv,
                            np.array([95, 80, 50], np.uint8),
                            np.array([135, 255, 255], np.uint8))
    return float(np.mean(blue_mask > 0)) > 0.55
 
 
# ── YOLO 검출 ─────────────────────────────────────────────────
 
def _detect_yolo(
    frame: np.ndarray,
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], np.ndarray]]:
    """YOLO 모델로 번호판 후보 검출. 미로드 시 빈 리스트 반환."""
    with _YOLO_LOCK:
        model = _YOLO_MODEL
    if model is None:
        return []
 
    h_f, w_f = frame.shape[:2]
    try:
        results = model(frame, conf=_YOLO_CONF, verbose=False, device=_YOLO_DEVICE)
    except Exception as e:
        print(f"[Detector] YOLO 추론 오류: {e}")
        return []
 
    candidates = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            coords = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords
            w0 = x2 - x1; h0 = y2 - y1
            if w0 < 20 or h0 < 10:
                continue
            # ★ 배경의 멀리 있는 다른 차 번호판 제거: 대상 차는 화면에서 크게 잡힘.
            #   가로폭이 프레임 폭의 일정 비율 미만이면 배경 차로 보고 버린다.
            if w0 < w_f * MIN_PLATE_W_FRAC:
                continue
            aspect = w0 / max(h0, 1)
            if not (MIN_ASPECT < aspect < MAX_ASPECT):
                continue
            # ★ YOLO 박스는 글자에 타이트하게 학습됨 → 패딩 추가로 끝자리 잘림 방지
            #   긴 번호판일수록 좌우 끝자리가 박스 밖으로 밀려 잘리므로 가로 패딩을
            #   크게(28%) 줌. 세로는 위아래 여백이 과하면 노이즈라 15% 유지.
            pad_x = int(w0 * 0.18); pad_y = int(h0 * 0.15)
            x1 = max(0, x1 - pad_x); y1 = max(0, y1 - pad_y)
            x2 = min(w_f, x2 + pad_x); y2 = min(h_f, y2 + pad_y)
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            w = x2 - x1; h = y2 - y1
            # ★ contour=None → preprocess_for_ocr가 YOLO 경량 경로 사용
            #   (YOLO crop은 이미 깨끗 → deskew/strip/morph/언샤프 불필요)
            candidates.append((roi, (x1, y1, w, h), None))

    return candidates


# ── YOLO 추적(Track) ──────────────────────────────────────────
#   ByteTrack으로 검출된 번호판에 track_id를 부여해 프레임마다 위치를
#   갱신한다. 영상 UI에서 박스가 대상을 실시간으로 따라다니다 대상이
#   사라지면 자동으로 없어지게 하기 위한 용도. (OCR과 분리)
#
#   ★ track()은 프레임 간 상태(persist)를 유지하므로 반드시 '순차'로
#     호출해야 한다. 같은 모델 인스턴스에 detect(model())와 track을
#     번갈아 쓰면 상태가 꼬이므로, 영상 모드에서는 track만 사용한다.

def track_plates(
    frame: np.ndarray,
) -> List[Tuple[int, int, int, int, int, np.ndarray]]:
    """
    YOLO track 모드로 번호판을 추적.
    반환: [(x, y, w, h, track_id, roi), ...]  (track_id 없으면 -1)
    미로드 시 빈 리스트.
    """
    with _YOLO_LOCK:
        model = _YOLO_MODEL
    if model is None:
        return []

    h_f, w_f = frame.shape[:2]
    try:
        results = model.track(
            frame, conf=_YOLO_CONF, persist=True,
            tracker="bytetrack.yaml", verbose=False, device=_YOLO_DEVICE,
        )
    except Exception as e:
        print(f"[Detector] YOLO track 오류: {e}")
        return []

    out: List[Tuple[int, int, int, int, int, np.ndarray]] = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            coords = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords
            w0 = x2 - x1; h0 = y2 - y1
            if w0 < 20 or h0 < 10:
                continue
            if w0 < w_f * MIN_PLATE_W_FRAC:
                continue
            aspect = w0 / max(h0, 1)
            if not (MIN_ASPECT < aspect < MAX_ASPECT):
                continue
            tid = int(box.id[0]) if box.id is not None else -1
            # OCR용 crop은 끝자리 잘림 방지 위해 패딩 (detect와 동일)
            pad_x = int(w0 * 0.18); pad_y = int(h0 * 0.15)
            cx1 = max(0, x1 - pad_x); cy1 = max(0, y1 - pad_y)
            cx2 = min(w_f, x2 + pad_x); cy2 = min(h_f, y2 + pad_y)
            roi = frame[cy1:cy2, cx1:cx2]
            if roi.size == 0:
                continue
            # 화면 박스는 원본 검출 좌표(패딩 전)를 쓴다 — 글자에 타이트하게.
            out.append((int(x1), int(y1), int(w0), int(h0), tid, roi))

    return out


# ── 프레임 내 초록(구식) 번호판 색 존재 여부 (저비용) ──────────

def _frame_has_green(frame: np.ndarray) -> bool:
    """초록·황록 픽셀이 일정량 이상이면 True. 초록 구식판 가능성."""
    small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
    hsv   = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    lo, hi = HSV_RANGES["GREENYELLOW"]
    mask  = cv2.inRange(hsv, lo, hi)
    return int(cv2.countNonZero(mask)) > 30   # 160×90 중 ~0.2%


# ── 초록(구식) 번호판 전용 검출 (HSV 마스크 기반) ───────────────

def _detect_green_plates(
    frame: np.ndarray,
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], np.ndarray]]:
    """
    초록색을 직접 마스킹해 구형 초록판(특히 2줄)을 검출.
    YOLO·회색조 Otsu 폴백이 밝은 차체에 묻혀 놓치는 경우를 보완.
    2줄 구형판은 거의 정사각이라 종횡비 하한을 1.0까지 낮춰서 허용한다.
    """
    h_f, w_f = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lo, hi = HSV_RANGES["GREENYELLOW"]
    mask = cv2.inRange(hsv, lo, hi)
    # 글자 사이 끊김을 메워 번호판을 하나의 덩어리로
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if not (MIN_AREA < area < w_f * h_f * 0.25):
            continue
        aspect = w / max(h, 1)
        if not (1.0 < aspect < MAX_ASPECT):   # 2줄 구형판(정사각)까지 허용
            continue
        # 박스 안이 실제로 초록으로 차 있는지(차체 반사 같은 잡덩어리 배제)
        if float(np.mean(mask[y:y+h, x:x+w] > 0)) < 0.35:
            continue
        # 약간의 여백 패딩
        pad_x = int(w * 0.10); pad_y = int(h * 0.10)
        x1 = max(0, x - pad_x); y1 = max(0, y - pad_y)
        x2 = min(w_f, x + w + pad_x); y2 = min(h_f, y + h + pad_y)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            continue
        out.append((roi, (x1, y1, x2 - x1, y2 - y1), None))
    return out


# ── 번호판 후보 검출 (YOLO 우선 + HSV 폴백) ────────────────────

def detect_plate_candidates(
    frame: np.ndarray,
) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], np.ndarray]]:
    """
    YOLO(우선) + HSV 폴백으로 번호판 후보 (roi, bbox, contour) 리스트 반환.
    contour는 ROI 로컬 좌표계 (preprocess_for_ocr에서 perspective transform 사용).
    """
    if frame is None or frame.size == 0:
        return []
 
    h_f, w_f = frame.shape[:2]
    if h_f < MIN_FRAME_DIM or w_f < MIN_FRAME_DIM:
        return []
 
    # ── YOLO 우선 시도 ────────────────────────────────────────────
    yolo_cands = _detect_yolo(frame)
    # YOLO가 잡았고 초록판 색이 없으면 폴백 생략(현행 흰색판은 YOLO로 충분).
    # 초록판 색이 보이면 YOLO가 놓쳤을 수 있으므로 폴백도 돌려 합친다.
    has_green = _frame_has_green(frame)
    if yolo_cands and not has_green:
        return _nms(yolo_cands)

    # ── 초록(구식) 번호판 전용 HSV 검출 ─────────────────────────
    green_cands = _detect_green_plates(frame) if has_green else []

    # ── HSV 폴백 (YOLO 결과와 합쳐 NMS) ──────────────────────────
    clahe = _get_clahe()
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
 
    if float(np.mean(gray)) < 110:
        lut  = np.array([min(255, int((i/255.0)**0.6*255)) for i in range(256)], dtype=np.uint8)
        gray = cv2.LUT(gray, lut)
 
    enhanced = clahe.apply(gray)
    blurred  = cv2.GaussianBlur(enhanced, (5, 5), 0)
 
    candidates = []
 
    # 정방향 + 반전 이진화 모두 시도 (밝은 배경 / 어두운 배경 번호판 모두 대응)
    for thresh_inv in [False, True]:
        flag = (cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
                if thresh_inv else cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, binary = cv2.threshold(blurred, 0, 255, flag)
 
        kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morphed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
 
        contours, _ = cv2.findContours(morphed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
 
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (MIN_AREA < area < MAX_AREA):
                continue
 
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / max(h, 1)
            if not (MIN_ASPECT < aspect < MAX_ASPECT):
                continue
 
            hull_area = cv2.contourArea(cv2.convexHull(cnt))
            solidity  = area / hull_area if hull_area > 0 else 0
            if solidity < MIN_SOLID:
                continue
 
            if (w * h) > (w_f * h_f * 0.15):
                continue
 
            roi = frame[y: y + h, x: x + w]
            if roi.size == 0:
                continue
 
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            if float(np.mean(roi_gray)) < 30:
                continue
 
            edges        = cv2.Canny(roi_gray, 50, 150)
            edge_density = np.sum(edges > 0) / (roi_gray.size + 1e-6)
            if edge_density < 0.025:
                continue
 
            if _is_road_sign(roi):
                continue
 
            # ★ Bug Fix: findContours는 frame 좌표 반환 → ROI 로컬 좌표로 변환
            cnt_local = cnt - np.array([[[x, y]]], dtype=np.int32)
            candidates.append((roi, (x, y, w, h), cnt_local, edge_density))
 
    if not candidates:
        # 폴백이 빈손이어도 YOLO·초록 결과가 있으면 그걸 반환
        merged = yolo_cands + green_cands
        return _nms(merged) if merged else []

    # 중복 제거 (같은 위치 정방향/반전 이진화 중복 후보)
    candidates.sort(key=lambda c: c[3], reverse=True)
    seen: set = set()
    unique = []
    for item in candidates:
        bx, by, bw, bh = item[1]
        key = (bx // 10, by // 10, bw // 10, bh // 10)
        if key not in seen:
            seen.add(key)
            unique.append(item)
 
    # YOLO 결과를 앞에 두어 우선 보존 (NMS는 면적 큰 순 정렬이라
    # 겹치는 경우 더 정확한 YOLO 박스가 살아남도록)
    candidates_nms = (yolo_cands + green_cands
                      + [(roi, bbox, cnt) for roi, bbox, cnt, _ in unique])
    return _nms(candidates_nms)
 
 
# ── 색상 분류 ─────────────────────────────────────────────────
 
def classify_plate_color(plate_roi: np.ndarray) -> Tuple[str, str]:
    if plate_roi is None or plate_roi.size == 0:
        return "WHITE", "NEW"
 
    hsv    = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2HSV)
    h, w   = hsv.shape[:2]
    sample = hsv[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
 
    total  = max(1, sample.shape[0] * sample.shape[1])
    scores = {
        color: int(np.sum(cv2.inRange(sample, lo, hi) > 0))
        for color, (lo, hi) in HSV_RANGES.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] < 20:
        return "WHITE", "NEW"

    # ★ 유채색(초록·노랑·파랑 등)은 배경을 압도적으로 차지할 때만 채택.
    #   어두운 회색판이 바닥 반사 등으로 소량 초록에 걸려 OLD로 오분류되는 것 방지.
    #   진짜 초록(구식)판은 샘플의 대부분이 초록이라 비율이 높다.
    if best != "WHITE" and (scores[best] / total) < 0.20:
        return "WHITE", "NEW"

    return best, PLATE_TYPE_MAP.get(best, "NEW")
 
 
# ── Deskew ────────────────────────────────────────────────────
 
def _deskew_roi(roi: np.ndarray) -> np.ndarray:
    """minAreaRect로 기울어진 번호판 이미지 수평 보정."""
    if roi is None or roi.size == 0:
        return roi
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi.copy()
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(bw > 0))
    if len(coords) < 10:
        return roi
    angle = cv2.minAreaRect(coords)[2]
    if angle < -45:
        angle += 90
    # 1° 미만 보정 불필요, 30° 초과는 오검출 가능성
    if abs(angle) < 1.0 or abs(angle) > 30:
        return roi
    h, w = roi.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(roi, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


# ── 번호판 평탄화 (기하 보정) ─────────────────────────────────

def _rectify_plate(roi_bgr: np.ndarray) -> np.ndarray:
    """
    기울어지거나 대각선으로 찍힌 번호판을 4꼭짓점을 찾아 정면 직사각형으로
    평탄화(perspective rectify). 사각형을 못 찾으면 회전만 보정(deskew)으로 폴백.
    YOLO crop은 패딩 덕에 번호판 외곽 사각형이 안쪽에 보이므로 검출이 잘 된다.
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return roi_bgr
    h, w = roi_bgr.shape[:2]
    roi_area = float(w * h)
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY) if roi_bgr.ndim == 3 else roi_bgr

    g     = cv2.bilateralFilter(gray, 7, 50, 50)   # 글자 보존하며 노이즈 완화
    edges = cv2.Canny(g, 40, 120)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), 1)

    cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in cnts:
        area = cv2.contourArea(c)
        if area < roi_area * 0.20:          # 번호판은 crop의 상당 부분 차지
            continue
        peri   = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, bw, bh = cv2.boundingRect(approx)
            aspect = bw / max(bh, 1)
            if 1.8 < aspect < 8.0 and area > best_area:
                best, best_area = approx, area

    # (1) 깔끔한 4각형 → 원근 변환(perspective)
    if best is not None:
        rect  = _order_points(best.reshape(4, 2).astype(np.float32))
        dst_w = int(max(np.linalg.norm(rect[1] - rect[0]),
                        np.linalg.norm(rect[2] - rect[3])))
        dst_h = int(max(np.linalg.norm(rect[3] - rect[0]),
                        np.linalg.norm(rect[2] - rect[1])))
        if dst_w > 20 and dst_h > 8:
            dst = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
            M   = cv2.getPerspectiveTransform(rect, dst)
            return cv2.warpPerspective(roi_bgr, M, (dst_w, dst_h),
                                       borderMode=cv2.BORDER_REPLICATE)

    # (2) 4각형 실패 → 가장 큰 윤곽의 회전사각형으로 강한 기울기 보정
    big = [c for c in cnts if cv2.contourArea(c) > roi_area * 0.15]
    if big:
        rrect = cv2.minAreaRect(max(big, key=cv2.contourArea))
        (_, _), (rw, rh), _ = rrect
        if rw > 10 and rh > 10:
            box   = _order_points(cv2.boxPoints(rrect).astype(np.float32))
            dst_w = int(max(rw, rh)); dst_h = int(min(rw, rh))
            if dst_w > 20 and dst_h > 8 and (dst_w / dst_h) < 9:
                dst = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
                M   = cv2.getPerspectiveTransform(box, dst)
                return cv2.warpPerspective(roi_bgr, M, (dst_w, dst_h),
                                           borderMode=cv2.BORDER_REPLICATE)

    # (3) 그래도 실패 → 회전만 보정
    return _deskew_roi(roi_bgr)


# ── OCR 전처리 ────────────────────────────────────────────────
 
def preprocess_for_ocr(
    plate_roi:   np.ndarray,
    plate_color: str,
    contour:     Optional[np.ndarray] = None,
) -> np.ndarray:
    if plate_roi is None or plate_roi.size == 0:
        return np.zeros((NORM_HEIGHT, NORM_WIDTH), dtype=np.uint8)
 
    # ── YOLO 경로 (contour is None) ───────────────────────────────
    #   ★ 평탄화(기하 보정): 기울어진/대각선 번호판을 정면으로 폄.
    #   그 뒤 강제 resize·strip·morph·언샤프·반전은 숫자를 망가뜨리므로
    #   생략하고, 어두울 때만 가벼운 감마+CLAHE 후 OCR에 투입.
    if contour is None:
        plate_roi = _rectify_plate(plate_roi)   # 평탄화 전처리
        # ★ 초록(구식) 번호판: 흰 글자 vs 녹색 배경 → R채널이 대비 최대.
        #   회색조로 바꾸면 둘 다 밝아져 대비가 죽으므로 R채널 사용 + 2배 확대.
        if plate_color == "GREENYELLOW" and plate_roi.ndim == 3:
            # 초록 배경(G↑ R↓) + 흰 글자(R↑): R채널이 배경 억제에 가장 효과적
            gray = plate_roi[:, :, 2]   # BGR R채널
            gray = cv2.resize(gray, None, fx=2.0, fy=2.0,
                              interpolation=cv2.INTER_CUBIC)
            # 어두우면 감마 보정
            mean_v = float(np.mean(gray))
            if mean_v < 100:
                gamma = 0.5 if mean_v < 50 else 0.7
                lut = np.array([min(255, int((i/255.0)**gamma*255))
                                for i in range(256)], dtype=np.uint8)
                gray = cv2.LUT(gray, lut)
            clahe_g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
            gray = clahe_g.apply(gray)
        else:
            gray = (cv2.cvtColor(plate_roi, cv2.COLOR_BGR2GRAY)
                    if len(plate_roi.shape) == 3 else plate_roi)
            h0, w0 = gray.shape[:2]
            if h0 < 64:                          # 작으면 종횡비 유지 업스케일
                scale = 64.0 / h0
                gray = cv2.resize(gray, (int(w0 * scale), 64),
                                  interpolation=cv2.INTER_CUBIC)
            mean_b = float(np.mean(gray))
            if mean_b < 100:                     # 어두우면 감마 보정
                gamma = 0.5 if mean_b < 50 else 0.7
                lut   = np.array([min(255, int((i / 255.0) ** gamma * 255))
                                  for i in range(256)], dtype=np.uint8)
                gray  = cv2.LUT(gray, lut)
            clahe_y = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe_y.apply(gray)
        # ★ 둘레 여백 추가 → OCR 텍스트 검출기가 경계에 붙은
        #   끝글자(예: 148의 '1')를 버리지 않도록 함
        bx = max(8, int(gray.shape[1] * 0.06))
        by = max(8, int(gray.shape[0] * 0.10))
        gray = cv2.copyMakeBorder(gray, by, by, bx, bx,
                                  cv2.BORDER_CONSTANT, value=255)
        return gray

    warped = plate_roi

    # ── 1. Perspective Transform ──────────────────────────────────
    # contour는 반드시 ROI 로컬 좌표여야 함 (detect_plate_candidates에서 변환됨)
    if contour is not None:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx  = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) == 4:
            pts   = approx.reshape(4, 2).astype(np.float32)
            rect  = _order_points(pts)
            dst_w = int(max(np.linalg.norm(rect[1] - rect[0]),
                            np.linalg.norm(rect[2] - rect[3])))
            dst_h = int(max(np.linalg.norm(rect[3] - rect[0]),
                            np.linalg.norm(rect[2] - rect[1])))
            if dst_w > 20 and dst_h > 8:
                dst    = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
                M      = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(plate_roi, M, (dst_w, dst_h),
                                             borderMode=cv2.BORDER_REPLICATE)
        elif len(approx) > 4:
            # 4각형 근사 실패 시 minAreaRect 폴백
            rect_r = cv2.minAreaRect(contour)
            box    = cv2.boxPoints(rect_r).astype(np.float32)
            pts    = _order_points(box)
            dst_w  = int(max(np.linalg.norm(pts[1] - pts[0]),
                             np.linalg.norm(pts[2] - pts[3])))
            dst_h  = int(max(np.linalg.norm(pts[3] - pts[0]),
                             np.linalg.norm(pts[2] - pts[1])))
            if dst_w > 20 and dst_h > 8:
                dst    = np.float32([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]])
                M      = cv2.getPerspectiveTransform(pts, dst)
                warped = cv2.warpPerspective(plate_roi, M, (dst_w, dst_h),
                                             borderMode=cv2.BORDER_REPLICATE)
 
    # ── 2. Deskew (기울기 보정) ──────────────────────────────────
    warped = _deskew_roi(warped)
 
    # ── 3. 크기 정규화 ─────────────────────────────────────────
    nw = NORM_WIDTH * 2  if plate_color == "GREENYELLOW" else NORM_WIDTH
    nh = NORM_HEIGHT * 2 if plate_color == "GREENYELLOW" else NORM_HEIGHT
    resized = cv2.resize(warped, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    gray2   = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
 
    # ── 5. 어두운 이미지 감마 보정 ─────────────────────────────
    mean_bright = float(np.mean(gray2))
    if mean_bright < 100:
        gamma = 0.5 if mean_bright < 50 else 0.7
        lut   = np.array([
            min(255, int((i / 255.0) ** gamma * 255))
            for i in range(256)
        ], dtype=np.uint8)
        gray2 = cv2.LUT(gray2, lut)
        mean_bright = float(np.mean(gray2))
 
    # ── 6. CLAHE 대비 강화 (6×6 그리드) ────────────────────────
    clip   = 4.0 if mean_bright < 100 else 2.0
    clahe2 = cv2.createCLAHE(clipLimit=clip, tileGridSize=(6, 6))
    enhanced = clahe2.apply(gray2)
 
    # ── 6.5. Morphological Close (끊어진 획 연결, 최소화) ─────────
    k_close  = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, k_close, iterations=1)
 
    # ── 7. 언샤프 마스킹 (글자 선명화) — 너무 강하면 6→5 같은 오독 유발
    _gauss   = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=0.8)
    enhanced = cv2.addWeighted(enhanced, 1.4, _gauss, -0.4, 0)
 
    # ── 8. 어두운 배경 번호판 (흰 글자) 반전 ───────────────────
    if float(np.mean(enhanced)) < 100:
        enhanced = cv2.bitwise_not(enhanced)
 
    return enhanced
 
 
def _order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype=np.float32)
    s    = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect