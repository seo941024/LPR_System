"""
query_tool.py — DB 조회 / 차량 관리 CLI

사용 예:
  python query_tool.py all               # 최근 100건 조회
  python query_tool.py plate 123가4567   # 번호판 검색 (부분 일치)
  python query_tool.py date 2025-06-07   # 날짜 조회
  python query_tool.py stats             # 통계
  python query_tool.py add 123가4567 홍길동 "검정 소나타"  # 화이트리스트 등록
  python query_tool.py block 999다8888 "도주 차량"        # 블랙리스트 등록
  python query_tool.py unblock 999다8888                 # 블랙리스트 해제
  python query_tool.py blocklist                         # 블랙리스트 전체 조회
  python query_tool.py purge 90          # 90일 이전 기록 삭제 (확인 필요)
"""

import sys
from database import (
    get_connection, init_db,
    query_all, query_by_plate, query_by_date, query_statistics,
    add_whitelist, get_all_whitelist,
    add_blacklist, delete_blacklist, get_all_blacklist,
    purge_old_records,
)


def _header():
    print(f"{'ID':>5}  {'번호판':^14}  {'색상':^14}  {'타입':^4}  "
          f"{'신뢰도':>6}  {'시각':^20}  {'카메라':^8}")
    print("─" * 85)


def _row(r):
    try:
        print(f"{r['id']:>5}  {r['plate_text']:^14}  {r['plate_color']:^14}  "
              f"{r['plate_type']:^4}  {float(r['confidence']):>6.1%}  "
              f"{r['timestamp']:^20}  {r['camera_id']:^8}")
    except Exception:
        pass


def cmd_all(conn, limit=100):
    rows = query_all(conn, limit)
    if not rows:
        print("기록 없음")
        return
    print(f"\n[ 최근 {len(rows)}건 ]\n")
    _header()
    for r in rows:
        _row(r)


def cmd_plate(conn, plate_text):
    rows = query_by_plate(conn, plate_text)
    if not rows:
        print(f"'{plate_text}' 검색 결과 없음")
        return
    print(f"\n[ '{plate_text}' 검색 — {len(rows)}건 ]\n")
    _header()
    for r in rows:
        _row(r)


def cmd_date(conn, date_str):
    rows = query_by_date(conn, date_str)
    if not rows:
        print(f"날짜 '{date_str}' 기록 없음")
        return
    print(f"\n[ {date_str} — {len(rows)}건 ]\n")
    _header()
    for r in rows:
        _row(r)


def cmd_stats(conn):
    rows = query_statistics(conn)
    if not rows:
        print("통계 없음")
        return
    print("\n[ 타입·색상별 통계 ]\n")
    print(f"{'타입':^6}  {'색상':^14}  {'건수':>6}")
    print("─" * 32)
    for r in rows:
        print(f"{r['plate_type']:^6}  {r['plate_color']:^14}  {r['cnt']:>6}")


def cmd_add(conn, plate_text, owner="", desc=""):
    if add_whitelist(conn, plate_text, owner, desc):
        print(f"화이트리스트 등록: {plate_text} ({owner})")
    else:
        print(f"이미 등록된 번호판: {plate_text}")


def cmd_block(conn, plate_text, reason=""):
    if add_blacklist(conn, plate_text, reason):
        print(f"블랙리스트 등록: {plate_text} — {reason}")
    else:
        print(f"이미 차단된 번호판: {plate_text}")


def cmd_unblock(conn, plate_text):
    if delete_blacklist(conn, plate_text):
        print(f"블랙리스트 해제: {plate_text}")
    else:
        print(f"블랙리스트에 없음: {plate_text}")


def cmd_blocklist(conn):
    rows = get_all_blacklist(conn)
    if not rows:
        print("블랙리스트 없음")
        return
    print(f"\n[ 블랙리스트 — {len(rows)}건 ]\n")
    print(f"{'번호판':^14}  {'사유':^30}  {'등록일':^12}")
    print("─" * 62)
    for r in rows:
        print(f"{r['plate_text']:^14}  {r.get('reason',''):^30}  "
              f"{r.get('registered_at','')[:10]:^12}")


def cmd_purge(conn, days=90):
    # 실수 방지를 위한 확인 프롬프트
    confirm = input(f"{days}일 이전 기록을 삭제합니다. 계속하시겠습니까? (yes 입력): ")
    if confirm.strip().lower() != "yes":
        print("취소됨")
        return
    n = purge_old_records(conn, days)
    print(f"{days}일 이전 {n}건 삭제 완료")


def main():
    init_db()
    conn = get_connection()
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        conn.close()
        return

    cmd = args[0].lower()

    try:
        if cmd == "all":
            cmd_all(conn, int(args[1]) if len(args) > 1 else 100)
        elif cmd == "plate" and len(args) >= 2:
            cmd_plate(conn, args[1])
        elif cmd == "date" and len(args) >= 2:
            cmd_date(conn, args[1])
        elif cmd == "stats":
            cmd_stats(conn)
        elif cmd == "add" and len(args) >= 2:
            cmd_add(conn, args[1],
                    args[2] if len(args) > 2 else "",
                    args[3] if len(args) > 3 else "")
        elif cmd == "block" and len(args) >= 2:
            cmd_block(conn, args[1], args[2] if len(args) > 2 else "")
        elif cmd == "unblock" and len(args) >= 2:
            cmd_unblock(conn, args[1])
        elif cmd == "blocklist":
            cmd_blocklist(conn)
        elif cmd == "purge":
            cmd_purge(conn, int(args[1]) if len(args) > 1 else 90)
        else:
            print(__doc__)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
