import os
import sqlite3

# database.py와 동일하게 이 파일 옆의 parking.db 사용
db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parking.db")
con = sqlite3.connect(db)
con.execute('DELETE FROM plate_logs')
con.execute('DELETE FROM entry_exit_log')
con.commit()
con.close()
print('DB 초기화 완료 (인식기록 + 입출차기록 삭제)')
input('계속하려면 Enter...')
