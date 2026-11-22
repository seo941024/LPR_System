from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent  # 저장소 폴더 기준 경로

if __name__ == '__main__':
    model = YOLO("yolo11m.pt")

    model.train(
        data    = str(ROOT / "dataset.yaml"),
        epochs  = 100,
        imgsz   = 640,
        batch   = 16,
        device  = 0,
        workers = 4,
        patience = 20,
        project = str(ROOT / "runs"),
        name    = "plate_detect",
    )
