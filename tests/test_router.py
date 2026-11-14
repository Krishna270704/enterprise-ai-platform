import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"))
from app.router import route_query
def test_doc(): assert route_query("What is the refund policy?")=="documents"
def test_sql(): assert route_query("How many customers are there?")=="sql"
def test_analytics(): assert route_query("Show monthly sales trend")=="analytics"
