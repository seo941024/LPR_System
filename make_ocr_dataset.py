"""
PaddleOCR 파인튜닝용 데이터셋 준비
이미지 파일명 = 번호판 텍스트 (예: 01가0785.jpg -> "01가0785")
"""
import os
import random
from pathlib import Path
from tqdm import tqdm

IMAGES_DIR  = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\PlateSample\images"
OUTPUT_DIR  = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\ocr_dataset"
LIMIT       = 300000  # 30만장 사용
VAL_RATIO   = 0.1

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("이미지 수집 중...")
img_files = [f for f in Path(IMAGES_DIR).rglob("*")
             if f.suffix.lower() in (".jpg", ".jpeg", ".png")
             and f.parent.name != "train"]  # YOLO 데이터 제외

print(f"총 이미지: {len(img_files)}개")

random.shuffle(img_files)
img_files = img_files[:LIMIT]

val_count   = int(len(img_files) * VAL_RATIO)
val_files   = img_files[:val_count]
train_files = img_files[val_count:]

def write_label_file(files, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for img in tqdm(files):
            label = img.stem.split("-")[0]  # "-2", "-3" 같은 suffix 제거
            f.write(f"{img.absolute()}\t{label}\n")

print("train 라벨 생성 중...")
write_label_file(train_files, os.path.join(OUTPUT_DIR, "train_list.txt"))
print("val 라벨 생성 중...")
write_label_file(val_files, os.path.join(OUTPUT_DIR, "val_list.txt"))

print(f"\n완료! train: {len(train_files)}개, val: {val_count}개")
print(f"라벨 파일: {OUTPUT_DIR}")
