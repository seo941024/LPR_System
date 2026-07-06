"""
yolo_labels의 txt 파일 기준으로 train/val 분리
이미지도 같이 복사
"""
import os
import shutil
import random
from pathlib import Path
from tqdm import tqdm

LABELS_DIR = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\yolo_labels"
IMAGES_DIR = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\PlateSample\images\train"
OUT_TRAIN_IMG = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\dataset\images\train"
OUT_VAL_IMG   = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\dataset\images\val"
OUT_TRAIN_LBL = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\dataset\labels\train"
OUT_VAL_LBL   = r"C:\Users\AISW_203_106\Desktop\LPR_Parking\dataset\labels\val"
VAL_RATIO = 0.1

for d in [OUT_TRAIN_IMG, OUT_VAL_IMG, OUT_TRAIN_LBL, OUT_VAL_LBL]:
    os.makedirs(d, exist_ok=True)

txt_files = list(Path(LABELS_DIR).glob("*.txt"))[:100000]
print(f"총 라벨 수: {len(txt_files)}")

random.shuffle(txt_files)
val_count = int(len(txt_files) * VAL_RATIO)
val_files = txt_files[:val_count]
train_files = txt_files[val_count:]

# 이미지 인덱스 (stem 기준으로 O(1) 조회)
print("이미지 인덱싱 중...")
img_index = {f.stem: f for f in Path(IMAGES_DIR).rglob("*")
             if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
print(f"이미지 인덱스: {len(img_index)}개")

def copy_pair(lbl_files, out_img, out_lbl):
    skip = 0
    for lf in tqdm(lbl_files):
        stem = lf.stem
        img = img_index.get(stem)
        if img is None:
            skip += 1
            continue
        shutil.copy2(lf, Path(out_lbl) / lf.name)
        shutil.copy2(img, Path(out_img) / img.name)
    print(f"스킵: {skip}")

print("train 복사 중...")
copy_pair(train_files, OUT_TRAIN_IMG, OUT_TRAIN_LBL)
print("val 복사 중...")
copy_pair(val_files, OUT_VAL_IMG, OUT_VAL_LBL)
print("완료!")
