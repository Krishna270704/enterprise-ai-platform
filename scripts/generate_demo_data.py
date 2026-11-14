from pathlib import Path
import csv,random
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"data"/"sample_data"; DOCS=ROOT/"data"/"raw"/"documents"
OUT.mkdir(parents=True,exist_ok=True); DOCS.mkdir(parents=True,exist_ok=True); random.seed(7)
def write(name,headers,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f: w=csv.writer(f); w.writerow(headers); w.writerows(rows)
customers=[[f"C{i:03}",f"Customer {i}",random.choice(["Delhi","Gurugram","Noida","Jaipur"]),random.choice(["Retail","Business","Enterprise"])] for i in range(1,31)]
employees=[[f"E{i:03}",f"Employee {i}",random.choice(["Sales","HR","Finance","Operations","IT"]),random.choice(["Delhi","Gurugram","Noida"]),random.randrange(30000,100001,5000)] for i in range(1,16)]
products=[["P001","NovaBook Pro","Laptop",75000],["P002","NovaView 27","Monitor",18000],["P003","Wireless Mouse","Accessory",1200],["P004","NovaBook Air","Laptop",62000],["P005","USB-C Dock","Accessory",4500],["P006","NovaView 24","Monitor",12500]]
orders=[]; sales=[]
for i in range(1,121):
    customer=random.choice(customers); d=date(2026,1,1)+timedelta(days=random.randrange(300)); order=f"O{i:04}"; product=random.choice(products); qty=random.randint(1,4)
    orders.append([order,customer[0],d.isoformat(),random.choice(["Delivered","Delivered","Processing","Cancelled"]),customer[2]])
    sales.append([f"S{i:04}",order,product[0],qty,qty*product[3],d.isoformat(),customer[2]])
inventory=[[p[0],"Delhi Central Warehouse",random.randint(5,100),20] for p in products]
write("customers.csv",["customer_id","name","city","segment"],customers); write("employees.csv",["employee_id","name","department","city","salary"],employees)
write("products.csv",["product_id","name","category","price"],products); write("orders.csv",["order_id","customer_id","order_date","status","city"],orders)
write("sales.csv",["sale_id","order_id","product_id","quantity","revenue","sale_date","city"],sales); write("inventory.csv",["product_id","warehouse","stock","reorder_level"],inventory)
docs={"HR_Policy.txt":"TechNova synthetic demo HR policy. Casual leave requires manager approval. HR requests are submitted through the employee portal. Payroll is processed on the final working day of each month.","Refund_Return_Policy.txt":"TechNova synthetic demo return policy. Customers may request a return within 15 calendar days of delivery if unused and in original packaging. Refunds are processed after inspection, normally within 7 business days.","Inventory_Policy.txt":"TechNova synthetic demo inventory policy. Each product has a reorder level. Warehouse staff flag stock at or below reorder level for replenishment. Inventory is reviewed weekly.","Product_Catalogue.txt":"TechNova synthetic catalogue: NovaBook Pro laptop INR 75000; NovaView 27 monitor INR 18000; Wireless Mouse accessory INR 1200; NovaBook Air laptop INR 62000; USB-C Dock accessory INR 4500; NovaView 24 monitor INR 12500.","Financial_Report.txt":"TechNova synthetic demo financial note for 2026. Sales are generated for academic testing only, not actual company financial statements. Revenue equals product price multiplied by units sold."}
for name,body in docs.items(): (DOCS/name).write_text(body,encoding="utf-8")
print("Generated synthetic CSV data and five demo documents.")
