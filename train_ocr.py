"""
PaddleOCR 인식 모델 파인튜닝
"""
from paddleocr import PaddleOCR
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.as_posix()  # 저장소 폴더 기준 경로

if __name__ == '__main__':
    cmd = [
        sys.executable, "-m", "paddle.distributed.launch",
        "--gpus", "0",
        "-m", "paddleocr.tools.train",
        "-c", "configs/rec/PP-OCRv4/ch_PP-OCRv4_rec.yml",
        "-o",
        "Global.pretrained_model=ch_PP-OCRv4_rec_train/best_accuracy",
        "Global.character_dict_path=ppocr/utils/ppocr_keys_v1.txt",
        f"Train.dataset.data_dir={ROOT}/PlateSample/images",
        f"Train.dataset.label_file_list=[{ROOT}/ocr_dataset/train_list.txt]",
        f"Eval.dataset.data_dir={ROOT}/PlateSample/images",
        f"Eval.dataset.label_file_list=[{ROOT}/ocr_dataset/val_list.txt]",
        f"Global.save_model_dir={ROOT}/ocr_output",
        "Train.loader.batch_size_per_card=128",
        "Global.epoch_num=50",
        "Global.eval_batch_step=[0,1000]",
    ]
    subprocess.run(cmd)
