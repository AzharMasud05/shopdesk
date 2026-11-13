from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, secrets
from datetime import datetime

APP_DIR=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(APP_DIR,"shop.db")
app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret-key-before-deployment")

def db():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init_db():
    con=db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','manager','salesman')));
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT, size TEXT, color TEXT, purchase_price REAL NOT NULL DEFAULT 0, selling_price REAL NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS locations(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
    CREATE TABLE IF NOT EXISTS stock(product_id INTEGER NOT NULL REFERENCES products(id), location_id INTEGER NOT NULL REFERENCES locations(id), qty INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(product_id,location_id));
    CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL REFERENCES products(id), from_location INTEGER, to_location INTEGER, qty INTEGER NOT NULL, note TEXT, user_id INTEGER REFERENCES users(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, invoice TEXT UNIQUE NOT NULL, total REAL NOT NULL, paid REAL NOT NULL, payment_method TEXT NOT NULL, customer TEXT, user_id INTEGER REFERENCES users(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER REFERENCES sales(id), product_id INTEGER REFERENCES products(id), qty INTEGER NOT NULL, unit_price REAL NOT NULL, unit_cost REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS cash_entries(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, amount REAL NOT NULL, category TEXT, note TEXT, user_id INTEGER REFERENCES users(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, action TEXT, detail TEXT, user_id INTEGER REFERENCES users(id), created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    for name in ("Godown","Showroom"):
        con.execute("INSERT OR IGNORE INTO locations(name) VALUES(?)",(name,))
    if not con.execute("SELECT 1 FROM users").fetchone():
        con.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",("admin",generate_password_hash("Admin@123"),"admin"))
    con.commit(); con.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if "uid" not in session: return redirect(url_for("login"))
        return fn(*a,**kw)
    return wrapped

def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if "uid" not in session: return redirect(url_for("login"))
            if session.get("role") not in allowed:
                flash("আপনার এই কাজের অনুমতি নেই / Permission denied","danger")
                return redirect(url_for("dashboard"))
            return fn(*a,**kw)
        return wrapped
    return deco

def audit(action,detail):
    con=db(); con.execute("INSERT INTO audit(action,detail,user_id) VALUES(?,?,?)",(action,detail,session.get("uid"))); con.commit(); con.close()

@app.context_processor
def common():
    return {"current_user":session.get("username"),"role":session.get("role")}

@app.route("/")
def home(): return redirect(url_for("dashboard") if session.get("uid") else url_for("login"))

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        con=db(); u=con.execute("SELECT * FROM users WHERE username=?",(request.form["username"].strip(),)).fetchone(); con.close()
        if u and check_password_hash(u["password"],request.form["password"]):
            session.update(uid=u["id"],username=u["username"],role=u["role"])
            return redirect(url_for("dashboard"))
        flash("ভুল ইউজারনেম বা পাসওয়ার্ড / Invalid login","danger")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    con=db()
    products=con.execute("SELECT COUNT(*) n FROM products").fetchone()["n"]
    total_stock=con.execute("SELECT COALESCE(SUM(qty),0) n FROM stock").fetchone()["n"]
    today=con.execute("SELECT COALESCE(SUM(total),0) n FROM sales WHERE date(created_at)=date('now','localtime')").fetchone()["n"]
    month=con.execute("SELECT COALESCE(SUM(total),0) n FROM sales WHERE strftime('%Y-%m',created_at)=strftime('%Y-%m','now','localtime')").fetchone()["n"]
    locations=con.execute("""SELECT l.name,COALESCE(SUM(s.qty),0) qty FROM locations l LEFT JOIN stock s ON s.location_id=l.id GROUP BY l.id""").fetchall()
    recent=con.execute("SELECT invoice,total,created_at FROM sales ORDER BY id DESC LIMIT 6").fetchall()
    low=con.execute("""SELECT p.code,p.name,COALESCE(SUM(s.qty),0) qty FROM products p LEFT JOIN stock s ON p.id=s.product_id GROUP BY p.id HAVING qty<=5 ORDER BY qty LIMIT 8""").fetchall()
    con.close()
    return render_template("dashboard.html",products=products,total_stock=total_stock,today=today,month=month,locations=locations,recent=recent,low=low)

@app.route("/products",methods=["GET","POST"])
@login_required
def products():
    con=db()
    if request.method=="POST":
        try:
            con.execute("""INSERT INTO products(code,name,category,size,color,purchase_price,selling_price) VALUES(?,?,?,?,?,?,?)""",
              (request.form["code"].strip(),request.form["name"].strip(),request.form.get("category",""),request.form.get("size",""),request.form.get("color",""),float(request.form.get("purchase_price") or 0),float(request.form.get("selling_price") or 0)))
            pid=con.execute("SELECT id FROM products WHERE code=?",(request.form["code"].strip(),)).fetchone()["id"]
            loc=con.execute("SELECT id FROM locations WHERE name='Godown'").fetchone()["id"]
            qty=int(request.form.get("opening_qty") or 0)
            if qty: con.execute("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?)",(pid,loc,qty))
            con.commit(); audit("PRODUCT_ADD",request.form["code"]); flash("পণ্য যোগ হয়েছে / Product added","success")
        except sqlite3.IntegrityError: con.rollback(); flash("এই Product Code আগে থেকেই আছে","danger")
        except Exception as e: con.rollback(); flash(str(e),"danger")
        con.close(); return redirect(url_for("products"))
    rows=con.execute("""SELECT p.*,COALESCE(SUM(CASE WHEN l.name='Godown' THEN s.qty ELSE 0 END),0) godown,COALESCE(SUM(CASE WHEN l.name='Showroom' THEN s.qty ELSE 0 END),0) showroom FROM products p LEFT JOIN stock s ON s.product_id=p.id LEFT JOIN locations l ON l.id=s.location_id GROUP BY p.id ORDER BY p.id DESC""").fetchall()
    con.close(); return render_template("products.html",products=rows)

@app.route("/stock",methods=["GET","POST"])
@login_required
def stock():
    con=db()
    if request.method=="POST":
        p=con.execute("SELECT id FROM products WHERE code=? OR id=?",(request.form["product"],request.form["product"] if request.form["product"].isdigit() else "-1")).fetchone()
        loc=con.execute("SELECT id FROM locations WHERE name=?",(request.form["location"],)).fetchone()
        qty=int(request.form["qty"])
        if not p or not loc or qty<0:
            flash("পণ্য/লোকেশন সঠিক নয় এবং পরিমাণ ০ বা তার বেশি হতে হবে","danger")
        else:
            con.execute("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?) ON CONFLICT(product_id,location_id) DO UPDATE SET qty=qty+excluded.qty",(p["id"],loc["id"],qty))
            con.execute("INSERT INTO movements(product_id,to_location,qty,note,user_id) VALUES(?,?,?,?,?)",(p["id"],loc["id"],qty,request.form.get("note","Manual stock addition"),session["uid"]))
            con.commit(); audit("STOCK_ADD",f'{request.form["product"]} +{qty} at {request.form["location"]}'); flash("স্টক যোগ হয়েছে / Stock added","success")
        con.close(); return redirect(url_for("stock"))
    rows=con.execute("""SELECT p.code,p.name,l.name location,s.qty FROM stock s JOIN products p ON p.id=s.product_id JOIN locations l ON l.id=s.location_id ORDER BY p.name,l.name""").fetchall()
    locs=con.execute("SELECT name FROM locations").fetchall(); con.close()
    return render_template("stock.html",rows=rows,locations=locs)

@app.route("/transfer",methods=["GET","POST"])
@roles("admin","manager")
def transfer():
    con=db()
    if request.method=="POST":
        p=con.execute("SELECT id FROM products WHERE code=?",(request.form["code"].strip(),)).fetchone()
        src=con.execute("SELECT id FROM locations WHERE name=?",(request.form["source"],)).fetchone()
        dst=con.execute("SELECT id FROM locations WHERE name=?",(request.form["destination"],)).fetchone()
        qty=int(request.form["qty"])
        if not p or not src or not dst or src["id"]==dst["id"] or qty<=0:
            flash("তথ্য সঠিকভাবে দিন / Check transfer details","danger")
        else:
            current=con.execute("SELECT qty FROM stock WHERE product_id=? AND location_id=?",(p["id"],src["id"])).fetchone()
            if not current or current["qty"]<qty: flash("উৎস লোকেশনে পর্যাপ্ত স্টক নেই / Insufficient stock","danger")
            else:
                con.execute("UPDATE stock SET qty=qty-? WHERE product_id=? AND location_id=?",(qty,p["id"],src["id"]))
                con.execute("INSERT INTO stock(product_id,location_id,qty) VALUES(?,?,?) ON CONFLICT(product_id,location_id) DO UPDATE SET qty=qty+excluded.qty",(p["id"],dst["id"],qty))
                con.execute("INSERT INTO movements(product_id,from_location,to_location,qty,note,user_id) VALUES(?,?,?,?,?,?)",(p["id"],src["id"],dst["id"],qty,request.form.get("note",""),session["uid"]))
                con.commit(); audit("TRANSFER",f'{request.form["code"]} {qty}: {request.form["source"]} -> {request.form["destination"]}'); flash("স্টক ট্রান্সফার সম্পন্ন / Transfer complete","success")
        con.close(); return redirect(url_for("transfer"))
    locs=con.execute("SELECT name FROM locations").fetchall()
    history=con.execute("""SELECT p.code,p.name,a.name src,b.name dst,m.qty,m.created_at FROM movements m JOIN products p ON p.id=m.product_id LEFT JOIN locations a ON a.id=m.from_location LEFT JOIN locations b ON b.id=m.to_location WHERE m.from_location IS NOT NULL ORDER BY m.id DESC LIMIT 20""").fetchall()
    con.close(); return render_template("transfer.html",locations=locs,history=history)

@app.route("/sales",methods=["GET","POST"])
@login_required
def sales():
    con=db()
    if request.method=="POST":
        code=request.form["code"].strip(); qty=int(request.form["qty"]); location=con.execute("SELECT id FROM locations WHERE name='Showroom'").fetchone()["id"]
        p=con.execute("SELECT * FROM products WHERE code=?",(code,)).fetchone()
        s=con.execute("SELECT qty FROM stock WHERE product_id=? AND location_id=?",(p["id"],location)).fetchone() if p else None
        if not p or qty<=0 or not s or s["qty"]<qty:
            flash("পণ্য পাওয়া যায়নি অথবা শোরুমে পর্যাপ্ত স্টক নেই","danger")
        else:
            price=float(request.form.get("unit_price") or p["selling_price"]); total=price*qty; paid=float(request.form.get("paid") or total)
            if price<0 or paid<0: flash("মূল্য সঠিক নয়","danger")
            else:
                invoice="INV-"+datetime.now().strftime("%y%m%d%H%M%S")+"-"+secrets.token_hex(2).upper()
                cur=con.execute("INSERT INTO sales(invoice,total,paid,payment_method,customer,user_id) VALUES(?,?,?,?,?,?)",(invoice,total,paid,request.form["payment_method"],request.form.get("customer",""),session["uid"]))
                sid=cur.lastrowid
                con.execute("INSERT INTO sale_items(sale_id,product_id,qty,unit_price,unit_cost) VALUES(?,?,?,?,?)",(sid,p["id"],qty,price,p["purchase_price"]))
                con.execute("UPDATE stock SET qty=qty-? WHERE product_id=? AND location_id=?",(qty,p["id"],location))
                con.execute("INSERT INTO cash_entries(kind,amount,category,note,user_id) VALUES('income',?,'Sale',?,?)",(paid,invoice,session["uid"]))
                con.commit(); audit("SALE",f"{invoice} {total}"); flash(f"বিক্রি সম্পন্ন / Sale complete: {invoice}","success")
        con.close(); return redirect(url_for("sales"))
    rows=con.execute("""SELECT s.*,u.username FROM sales s LEFT JOIN users u ON u.id=s.user_id ORDER BY s.id DESC LIMIT 30""").fetchall()
    con.close(); return render_template("sales.html",sales=rows)

@app.route("/accounts",methods=["GET","POST"])
@roles("admin","manager")
def accounts():
    con=db()
    if request.method=="POST":
        amount=float(request.form["amount"])
        if amount<=0: flash("Amount must be greater than zero","danger")
        else:
            con.execute("INSERT INTO cash_entries(kind,amount,category,note,user_id) VALUES(?,?,?,?,?)",(request.form["kind"],amount,request.form["category"],request.form.get("note",""),session["uid"]))
            con.commit(); audit("ACCOUNT_ENTRY",f'{request.form["kind"]} {amount}'); flash("হিসাব সংরক্ষিত হয়েছে","success")
        con.close(); return redirect(url_for("accounts"))
    entries=con.execute("SELECT * FROM cash_entries ORDER BY id DESC LIMIT 100").fetchall()
    totals=con.execute("SELECT COALESCE(SUM(CASE WHEN kind='income' THEN amount ELSE 0 END),0) income,COALESCE(SUM(CASE WHEN kind='expense' THEN amount ELSE 0 END),0) expense FROM cash_entries").fetchone()
    con.close(); return render_template("accounts.html",entries=entries,totals=totals)

@app.route("/reports")
@roles("admin","manager")
def reports():
    con=db()
    rows=con.execute("""SELECT p.code,p.name,p.purchase_price,p.selling_price,COALESCE(SUM(si.qty),0) sold,COALESCE(SUM(si.qty*(si.unit_price-si.unit_cost)),0) gross_profit FROM products p LEFT JOIN sale_items si ON si.product_id=p.id GROUP BY p.id ORDER BY sold DESC""").fetchall()
    daily=con.execute("SELECT date(created_at) day,SUM(total) sales,COUNT(*) invoices FROM sales GROUP BY date(created_at) ORDER BY day DESC LIMIT 30").fetchall()
    con.close(); return render_template("reports.html",rows=rows,daily=daily)

@app.route("/users",methods=["GET","POST"])
@roles("admin")
def users():
    con=db()
    if request.method=="POST":
        try:
            con.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",(request.form["username"].strip(),generate_password_hash(request.form["password"]),request.form["role"]))
            con.commit(); flash("ব্যবহারকারী তৈরি হয়েছে / User created","success")
        except sqlite3.IntegrityError: flash("Username already exists","danger")
        con.close(); return redirect(url_for("users"))
    rows=con.execute("SELECT id,username,role FROM users ORDER BY id").fetchall(); con.close()
    return render_template("users.html",users=rows)

@app.route("/audit")
@roles("admin")
def audit_log():
    con=db(); rows=con.execute("SELECT a.*,u.username FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 100").fetchall(); con.close()
    return render_template("audit.html",rows=rows)

@app.route("/api/product/<code>")
@login_required
def product_lookup(code):
    con=db(); p=con.execute("SELECT code,name,selling_price FROM products WHERE code=?",(code,)).fetchone(); con.close()
    return jsonify(dict(p) if p else {})

if __name__=="__main__":
    init_db()
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
