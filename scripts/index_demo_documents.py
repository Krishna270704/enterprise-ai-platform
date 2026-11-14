import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"backend"))
from app.ingestion import index_document
for p in (ROOT/"data"/"raw"/"documents").glob("*"):
    if p.is_file():
        try: print(index_document(p))
        except Exception as e: print("FAILED",p.name,e)
