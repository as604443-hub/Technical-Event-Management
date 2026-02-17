from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = "secret_key"

# ---------------- DATABASE ---------------- #

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS membership(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_number TEXT UNIQUE,
        name TEXT,
        email TEXT,
        duration TEXT,
        status TEXT,
        expiry_date TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ------------- SESSION PROTECTION ------------ #

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/login')

            if role and session.get('role') != role:
                return "Access Denied"

            return f(*args, **kwargs)
        return wrapper
    return decorator

# ---------------- AUTH ---------------- #

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if not name or not email or not password:
            return "All fields mandatory!"

        conn = get_db()
        conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                     (name,email,password,role))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                            (email,password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']

            if user['role'] == "admin":
                return redirect('/admin_dashboard')
            else:
                return redirect('/user_dashboard')

        return "Invalid Credentials"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- DASHBOARDS ---------------- #

@app.route('/admin_dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template("admin_dashboard.html")

@app.route('/user_dashboard')
@login_required()
def user_dashboard():
    return render_template("user_dashboard.html")

# ---------------- MAINTENANCE ---------------- #

@app.route('/maintenance')
@login_required(role='admin')
def maintenance():
    return render_template("maintenance.html")

# ---------------- ADD MEMBERSHIP ---------------- #

@app.route('/add_membership', methods=['GET','POST'])
@login_required(role='admin')
def add_membership():
    if request.method == 'POST':
        membership_number = str(uuid.uuid4())[:8]
        name = request.form['name']
        email = request.form['email']
        duration = request.form['duration']

        if not name or not email:
            return "All fields mandatory!"

        expiry_map = {
            "6 months": "+6 months",
            "1 year": "+12 months",
            "2 years": "+24 months"
        }

        conn = get_db()
        conn.execute(f"""
        INSERT INTO membership 
        (membership_number,name,email,duration,status,expiry_date)
        VALUES (?,?,?,?,?,date('now','{expiry_map[duration]}'))
        """,(membership_number,name,email,duration,"Active"))

        conn.commit()
        conn.close()

        return redirect('/maintenance')

    return render_template("add_membership.html")

# ---------------- UPDATE MEMBERSHIP ---------------- #

@app.route('/update_membership', methods=['GET','POST'])
@login_required(role='admin')
def update_membership():
    conn = get_db()

    if request.method == 'POST':
        membership_number = request.form['membership_number']
        action = request.form['action']

        member = conn.execute("SELECT * FROM membership WHERE membership_number=?",
                              (membership_number,)).fetchone()

        if not member:
            conn.close()
            return "Membership Not Found!"

        if action == "extend":
            conn.execute("""
            UPDATE membership 
            SET expiry_date = date(expiry_date,'+6 months') 
            WHERE membership_number=?
            """,(membership_number,))
        else:
            conn.execute("""
            UPDATE membership 
            SET status='Cancelled'
            WHERE membership_number=?
            """,(membership_number,))

        conn.commit()
        conn.close()

        return redirect('/maintenance')

    conn.close()
    return render_template("update_membership.html")

# ---------------- REPORTS ---------------- #

@app.route('/reports')
@login_required()
def reports():
    conn = get_db()
    members = conn.execute("SELECT * FROM membership").fetchall()
    conn.close()
    return render_template("reports.html", members=members)

# ---------------- TRANSACTIONS ---------------- #

@app.route('/transactions')
@login_required()
def transactions():
    return render_template("transactions.html")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)