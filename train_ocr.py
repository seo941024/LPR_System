"""
PaddleOCR 인식 모델 파인튜닝
"""
from paddleocr import PaddleOCR
import subprocess
import sys

if __name__ == '__main__':
    cmd = [
        sys.executable, "-m", "paddle.distributed.launch",
        "--gpus", "0",
        "-m", "paddleocr.tools.train",
        "-c", "configs/rec/PP-OCRv4/ch_PP-OCRv4_rec.yml",
        "-o",
        "Global.pretrained_model=ch_PP-OCRv4_rec_train/best_accuracy",
        "Global.character_dict_path=ppocr/utils/ppocr_keys_v1.txt",
        "Train.dataset.data_dir=C:/Users/AISW_203_106/Desktop/LPR_Parking/PlateSample/images",
        "Train.dataset.label_file_list=[C:/Users/AISW_203_106/Desktop/LPR_Parking/ocr_dataset/train_list.txt]",
        "Eval.dataset.data_dir=C:/Users/AISW_203_106/Desktop/LPR_Parking/PlateSample/images",
        "Eval.dataset.label_file_list=[C:/Users/AISW_203_106/Desktop/LPR_Parking/ocr_dataset/val_list.txt]",
        "Global.save_model_dir=C:/Users/AISW_203_106/Desktop/LPR_Parking/ocr_output",
        "Train.loader.batch_size_per_card=128",
        "Global.epoch_num=50",
        "Global.eval_batch_step=[0,1000]",
    ]
    subprocess.run(cmd)
