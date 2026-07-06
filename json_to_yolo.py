"""
AIHub 번호판 JSON 라벨 → YOLO txt 포맷 변환
JSON: {"imagePath": "xxx.jpg", "plate": {"bbox": [[x1,y1],[x2,y2]]}, ...}
YOLO: 0 cx cy w h (정규화)
"""
import json
import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm

ANNOTATIONS_DIR = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\PlateSample\annotations"
IMAGES_DIR      = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\PlateSample\images\train"
OUTPUT_LABELS   = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\yolo_labels"

os.makedirs(OUTPUT_LABELS, exist_ok=True)

json_files = list(Path(ANNOTATIONS_DIR).rglob("*.json"))[:500000]
print(f"JSON 파일 수: {len(json_files)}")

# 이미지 인덱스 미리 구성 (파일명 → 전체경로)
print("이미지 인덱싱 중...")
img_index = {f.name: f for f in Path(IMAGES_DIR).rglob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
print(f"이미지 인덱스: {len(img_index)}개")

ok, skip = 0, 0

for jf in tqdm(json_files):
    try:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)

        # car.imagePath 기준으로 이미지 찾기 (예: "트럭/트럭/트럭_기타-1.jpg")
        car = data.get("car", {})
        car_image_path = car.get("imagePath", "")
        img_name = Path(car_image_path).name  # "트럭_기타-1.jpg"

        img_file = img_index.get(img_name)
        if img_file is None:
            skip += 1
            continue

        plate = data.get("plate", {})
        bbox = plate.get("bbox")
        if not bbox or len(bbox) < 2:
            skip += 1
            continue

        # plate bbox는 원본 CCTV 이미지 기준 좌표 → car crop 이미지 기준으로 변환
        car_bbox = car.get("bbox")
        if not car_bbox or len(car_bbox) < 2:
            skip += 1
            continue

        car_x1, car_y1 = car_bbox[0]

        px1 = bbox[0][0] - car_x1
        py1 = bbox[0][1] - car_y1
        px2 = bbox[1][0] - car_x1
        py2 = bbox[1][1] - car_y1

        # 이미지 크기
        with Image.open(img_file) as img:
            iw, ih = img.size

        cx = ((px1 + px2) / 2) / iw
        cy = ((py1 + py2) / 2) / ih
        bw = abs(px2 - px1) / iw
        bh = abs(py2 - py1) / ih

        # 범위 체크
        if not (0 < cx < 1 and 0 < cy < 1 and 0 < bw < 1 and 0 < bh < 1):
            skip += 1
            continue

        label_file = Path(OUTPUT_LABELS) / (Path(img_name).stem + ".txt")
        with open(label_file, "w") as f:
            f.write(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

        ok += 1

    except Exception as e:
        skip += 1

print(f"\n완료: {ok}개 변환, {skip}개 스킵")
