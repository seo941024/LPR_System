from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("yolo11m.pt")

    model.train(
        data    = "C:/Users/AISW_203_106/Desktop/LPR_Parking/dataset.yaml",
        epochs  = 100,
        imgsz   = 640,
        batch   = 16,
        device  = 0,
        workers = 4,
        patience = 20,
        project = "C:/Users/AISW_203_106/Desktop/LPR_Parking/runs",
        name    = "plate_detect",
    )
