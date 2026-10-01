"""
load_demo_data.py — analytics/demo_parking.db의 합성 데이터를 실제 앱 DB(parking.db)로 불러온다.

실제 카메라 배포 전이라 parking.db가 비어있을 때, 대시보드/통계/검색 화면이
실제 데이터가 쌓인 것처럼 보이도록 데모 데이터를 채워 넣는 용도.
(포트폴리오 스크린샷 등 시연 목적)

실행:
    cd lpr_system
    python load_demo_data.py
"""
import os
import sqlite3
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO_DB = os.path.join(HERE, "..", "analytics", "demo_parking.db")
APP_DB = os.path.join(HERE, "parking.db")


def main():
    if not os.path.exists(DEMO_DB):
        print(f"데모 DB를 찾을 수 없습니다: {DEMO_DB}")
        print("먼저 analytics/generate_sample_data.py 를 실행해 생성하세요.")
        return

    # 앱 DB 스키마 보장 (없으면 생성)
    from database import init_db
    init_db()

    demo = sqlite3.connect(DEMO_DB)
    app = sqlite3.connect(APP_DB)

    demo.row_factory = sqlite3.Row
    app_cur = app.cursor()

    # 기존 데모 데이터 중복 적재 방지: source_file='demo'로 심어뒀던 이전 데모 로그 제거
    app_cur.execute("DELETE FROM plate_logs WHERE source_file = 'demo'")
    app_cur.execute(
        "DELETE FROM entry_exit_log WHERE plate_text IN "
        "(SELECT plate_text FROM plate_logs WHERE source_file = 'demo') "
        "OR image_path = 'demo'"
    )
    # whitelist는 plate_text UNIQUE라 INSERT OR IGNORE로 안전하게 추가

    n_plate = n_ee = n_wl = 0

    for row in demo.execute("SELECT * FROM plate_logs"):
        app_cur.execute(
            "INSERT INTO plate_logs "
            "(plate_text, plate_color, plate_type, confidence, timestamp, camera_id, image_path, frame_number, source_file) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (row["plate_text"], row["plate_color"], row["plate_type"], row["confidence"],
             row["timestamp"], row["camera_id"], row["image_path"], row["frame_number"], "demo"),
        )
        n_plate += 1

    for row in demo.execute("SELECT * FROM entry_exit_log"):
        app_cur.execute(
            "INSERT INTO entry_exit_log (plate_text, event_type, camera_id, timestamp, image_path) "
            "VALUES (?,?,?,?,?)",
            (row["plate_text"], row["event_type"], row["camera_id"], row["timestamp"], "demo"),
        )
        n_ee += 1

    for row in demo.execute("SELECT * FROM whitelist"):
        app_cur.execute(
            "INSERT OR IGNORE INTO whitelist (plate_text, owner_name, vehicle_desc, registered_at) "
            "VALUES (?,?,?,?)",
            (row["plate_text"], row["owner_name"], row["vehicle_desc"], row["registered_at"]),
        )
        n_wl += 1

    app.commit()
    demo.close()
    app.close()

    print(f"완료: plate_logs {n_plate}건, entry_exit_log {n_ee}건, whitelist {n_wl}건 불러옴")
    print(f"앱 DB: {APP_DB}")
    print("앱을 재시작하면 대시보드/통계/검색에 데모 데이터가 표시됩니다.")


if __name__ == "__main__":
    main()
