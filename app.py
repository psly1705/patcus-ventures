"""
PATCUS VENTURES - PWA Server
Block Factory Management System
SQLite version — data survives server restarts on Render
"""

from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__, template_folder='.')
app.secret_key = os.environ.get('SECRET_KEY', 'patcus_secret_key_2025_secure')

# ── Database path ──────────────────────────────────────────────────
# On Render with a Persistent Disk, mount it at /data and set
# the DATABASE_PATH env var to /data/patcus.db
# Otherwise it stores next to app.py (fine for local use)
DB_PATH = os.environ.get('DATABASE_PATH', 'patcus.db')

BLOCK_SIZES = ['5 inches Solid', '5 inches Hollow', '6 inches Solid', '6 inches Hollow']

DEFAULT_USERS = {
    "sylvester": {"password": "osei17",   "role": "system_admin", "name": "Osei Sylvester"},
    "nanapoku":  {"password": "patcus17", "role": "manager",      "name": "Nana Osei Poku Brempong"},
    "benjamin":  {"password": "benji45",  "role": "sales",        "name": "Benjamin"},
}

# ── Database setup ─────────────────────────────────────────────────
def get_db():
    """Open a database connection for the current request."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn

def init_db():
    """Create all tables if they don't exist, seed default users."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role     TEXT NOT NULL,
            name     TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            customer TEXT NOT NULL,
            contact  TEXT,
            size     TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            location TEXT,
            by       TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS revenues (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            type     TEXT NOT NULL,
            size     TEXT,
            quantity INTEGER DEFAULT 0,
            amount   REAL NOT NULL,
            desc     TEXT,
            by       TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            category TEXT NOT NULL,
            desc     TEXT,
            blocks   INTEGER DEFAULT 0,
            amount   REAL NOT NULL,
            by       TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS moulds (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            size         TEXT NOT NULL,
            palettes     INTEGER NOT NULL,
            total_blocks INTEGER NOT NULL,
            cement       INTEGER NOT NULL,
            by           TEXT
        )
    ''')

    # Seed / update default users
    for uname, udata in DEFAULT_USERS.items():
        existing = c.execute('SELECT username FROM users WHERE username=?', (uname,)).fetchone()
        if existing:
            # Update name and role but never overwrite a custom password
            c.execute('UPDATE users SET name=?, role=? WHERE username=?',
                      (udata['name'], udata['role'], uname))
        else:
            c.execute('INSERT INTO users (username, password, role, name) VALUES (?,?,?,?)',
                      (uname, udata['password'], udata['role'], udata['name']))

    # Remove old sales1 account if it migrated in somehow
    c.execute("DELETE FROM users WHERE username='sales1'")

    conn.commit()
    conn.close()

def today_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def is_system_admin():
    return session.get('role') == 'system_admin'

def logged_in():
    return 'username' in session

# Initialise DB on startup
init_db()

# ── Static file routes ─────────────────────────────────────────────
@app.route('/')
def index():
    if not logged_in():
        return send_from_directory('.', 'login.html')
    return send_from_directory('.', 'index.html')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def sw():
    return send_from_directory('.', 'service-worker.js')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ── Auth ───────────────────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    conn.close()
    if user and user['password'] == password:
        session['username']  = username
        session['role']      = user['role']
        session['user_name'] = user['name']
        return jsonify({'success': True, 'role': session['role'], 'name': session['user_name']})
    return jsonify({'success': False, 'error': 'Invalid username or password'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ── Get all data ───────────────────────────────────────────────────
@app.route('/api/get_data')
def get_data():
    if not logged_in():
        return jsonify({'error': 'Not logged in'}), 401

    conn = get_db()

    deliveries = [dict(r) for r in conn.execute(
        'SELECT * FROM deliveries ORDER BY id DESC LIMIT 200').fetchall()]
    revenues   = [dict(r) for r in conn.execute(
        'SELECT * FROM revenues ORDER BY id DESC LIMIT 200').fetchall()]
    expenses   = [dict(r) for r in conn.execute(
        'SELECT * FROM expenses ORDER BY id DESC LIMIT 200').fetchall()]
    moulds     = [dict(r) for r in conn.execute(
        'SELECT * FROM moulds ORDER BY id DESC LIMIT 200').fetchall()]

    # Inventory per block size
    inventory = {}
    for bt in BLOCK_SIZES:
        delivered = conn.execute(
            'SELECT COALESCE(SUM(quantity),0) FROM deliveries WHERE size=?', (bt,)).fetchone()[0]
        moulded   = conn.execute(
            'SELECT COALESCE(SUM(total_blocks),0) FROM moulds WHERE size=?', (bt,)).fetchone()[0]
        inventory[bt] = {
            'delivered': delivered,
            'moulded':   moulded,
            'remaining': moulded - delivered
        }

    total_rev = conn.execute('SELECT COALESCE(SUM(amount),0) FROM revenues').fetchone()[0]
    total_exp = conn.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]
    conn.close()

    # Reverse lists so newest is last (matches original frontend expectation)
    deliveries.reverse()
    revenues.reverse()
    expenses.reverse()
    moulds.reverse()

    return jsonify({
        'user_name':  session.get('user_name'),
        'role':       session.get('role'),
        'deliveries': deliveries,
        'revenues':   revenues,
        'expenses':   expenses,
        'moulds':     moulds,
        'inventory':  inventory,
        'stats': {
            'total_received': total_rev,
            'total_expenses': total_exp,
            'net_profit':     total_rev - total_exp
        }
    })

# ── Add operations ─────────────────────────────────────────────────
@app.route('/api/add_delivery', methods=['POST'])
def add_delivery():
    if not logged_in():
        return jsonify({'success': False, 'error': 'Not logged in'})
    data = request.json
    conn = get_db()
    conn.execute(
        'INSERT INTO deliveries (date, customer, contact, size, quantity, location, by) VALUES (?,?,?,?,?,?,?)',
        (today_str(), data.get('customer'), data.get('contact',''),
         data.get('size'), data.get('quantity'), data.get('location',''), session['username'])
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/add_revenue', methods=['POST'])
def add_revenue():
    if not logged_in():
        return jsonify({'success': False})
    data = request.json
    conn = get_db()
    if data.get('type') == 'Blocks Sale':
        conn.execute(
            'INSERT INTO revenues (date, type, size, quantity, amount, desc, by) VALUES (?,?,?,?,?,?,?)',
            (today_str(), 'Blocks Sale', data.get('size'), data.get('quantity', 0),
             data.get('amount', 0), '', session['username'])
        )
    else:
        conn.execute(
            'INSERT INTO revenues (date, type, size, quantity, amount, desc, by) VALUES (?,?,?,?,?,?,?)',
            (today_str(), 'Other Income', '', 0,
             data.get('amount', 0), data.get('description', ''), session['username'])
        )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/add_expense', methods=['POST'])
def add_expense():
    if not logged_in():
        return jsonify({'success': False})
    data  = request.json
    etype = data.get('type')
    blocks = data.get('blocks', 0)
    if etype == 'Loading':
        desc = f"Loading – {blocks} blocks" if blocks else "Loading"
    elif etype == 'Other':
        desc = data.get('description', 'Other Expense')
    else:
        desc = "Diesel"
    conn = get_db()
    conn.execute(
        'INSERT INTO expenses (date, category, desc, blocks, amount, by) VALUES (?,?,?,?,?,?)',
        (today_str(), etype, desc, blocks, data.get('amount'), session['username'])
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/add_mould', methods=['POST'])
def add_mould():
    if not logged_in():
        return jsonify({'success': False})
    data     = request.json
    size     = data.get('size')
    palettes = data.get('palettes')
    bpp      = 6 if '5' in size else 5
    total_blocks = palettes * bpp
    conn = get_db()
    conn.execute(
        'INSERT INTO moulds (date, size, palettes, total_blocks, cement, by) VALUES (?,?,?,?,?,?)',
        (today_str(), size, palettes, total_blocks, data.get('cement'), session['username'])
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── Delete operations — System Admin only ──────────────────────────
@app.route('/api/delete_delivery', methods=['POST'])
def delete_delivery():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    row_id = request.json.get('index')  # frontend still calls it 'index' but we store real DB id
    conn = get_db()
    conn.execute('DELETE FROM deliveries WHERE id=?', (row_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/delete_revenue', methods=['POST'])
def delete_revenue():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    row_id = request.json.get('index')
    conn = get_db()
    conn.execute('DELETE FROM revenues WHERE id=?', (row_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/delete_expense', methods=['POST'])
def delete_expense():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    row_id = request.json.get('index')
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id=?', (row_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/delete_mould', methods=['POST'])
def delete_mould():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    row_id = request.json.get('index')
    conn = get_db()
    conn.execute('DELETE FROM moulds WHERE id=?', (row_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── User management — System Admin only ───────────────────────────
@app.route('/api/get_users')
def get_users():
    if not is_system_admin():
        return jsonify({'error': 'System Administrator only'}), 403
    conn = get_db()
    rows = conn.execute('SELECT username, name, role FROM users').fetchall()
    conn.close()
    return jsonify({r['username']: {'name': r['name'], 'role': r['role']} for r in rows})

@app.route('/api/update_user', methods=['POST'])
def update_user():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data  = request.json
    uname = data.get('username')
    conn  = get_db()
    user  = conn.execute('SELECT username FROM users WHERE username=?', (uname,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'})
    if data.get('password'):
        conn.execute('UPDATE users SET password=? WHERE username=?', (data['password'], uname))
    if data.get('name'):
        conn.execute('UPDATE users SET name=? WHERE username=?', (data['name'], uname))
    if data.get('role'):
        conn.execute('UPDATE users SET role=? WHERE username=?', (data['role'], uname))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = '127.0.0.1'

    print("\n" + "="*55)
    print("🏭  PATCUS VENTURES — Block Factory Management")
    print("="*55)
    print(f"\n  📱 Mobile  :  http://{local_ip}:5000")
    print(f"  💻 Browser :  http://localhost:5000")
    print(f"\n  🗄️  Database : {DB_PATH}")
    print("\n  👤 SYSTEM ADMINISTRATOR")
    print("     Username : sylvester  |  Password : osei17")
    print("\n  👤 MANAGER")
    print("     Username : nanapoku   |  Password : patcus17")
    print("\n  👤 SALES")
    print("     Username : benjamin   |  Password : benji45")
    print("="*55 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
