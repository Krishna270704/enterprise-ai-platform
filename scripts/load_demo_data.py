import csv,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend"))
from app.db import init_db,connect
TABLES={"customers":"customers.csv","employees":"employees.csv","products":"products.csv","orders":"orders.csv","sales":"sales.csv","inventory":"inventory.csv"}
def load():
    init_db()
    with connect() as c:
        with c.cursor() as cur:
            for table,file in TABLES.items():
                with (ROOT/"data"/"sample_data"/file).open(encoding="utf-8") as f: rows=list(csv.DictReader(f))
                cur.execute(f"TRUNCATE TABLE {table} CASCADE")
                for row in rows:
                    cols=list(row); cur.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['%s']*len(cols))})",[row[x] for x in cols])
        c.commit()
    print("Loaded synthetic TechNova data.")
if __name__=="__main__": load()
