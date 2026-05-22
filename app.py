"""
PATCUS VENTURES - PWA Server
Block Factory Management System
"""

from flask import Flask, render_template, request, jsonify, session, send_from_directory
import json
import os
from datetime import datetime
from collections import defaultdict

app = Flask(__name__, template_folder='.')
app.secret_key = 'patcus_secret_key_2025_secure'

# ── Data paths ─────────────────────────────────────────────────────────────
DATA_DIR = "patcus_data"
os.makedirs(DATA_DIR, exist_ok=True)

DELIVERIES_FILE = os.path.join(DATA_DIR, "deliveries.json")
REVENUES_FILE   = os.path.join(DATA_DIR, "revenues.json")
EXPENSES_FILE   = os.path.join(DATA_DIR, "expenses.json")
MOULDS_FILE     = os.path.join(DATA_DIR, "moulds.json")
USERS_FILE      = os.path.join(DATA_DIR, "users.json")

# ── Users:
#    sylvester = system_admin  (full access, all permissions)
#    nanapoku  = manager       (can add data, view reports, NO delete)
#    sales1    = sales         (can add deliveries & revenue only)
DEFAULT_USERS = {
    "sylvester": {"password": "osei17",   "role": "system_admin", "name": "Osei Sylvester"},
    "nanapoku":  {"password": "patcus17", "role": "manager",      "name": "Nana Osei Poku Brempong"},
    "benjamin":  {"password": "benji45",  "role": "sales",        "name": "Benjamin"},
}

BLOCK_SIZES = ['5 inches Solid', '5 inches Hollow', '6 inches Solid', '6 inches Hollow']

# ── Helpers ────────────────────────────────────────────────────────────────
def load_data(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def today_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def is_system_admin():
    return session.get('role') == 'system_admin'

def is_manager_or_above():
    return session.get('role') in ('system_admin', 'manager')

def logged_in():
    return 'username' in session

if not os.path.exists(USERS_FILE):
    save_data(USERS_FILE, DEFAULT_USERS)
else:
    # Merge: add new users and remove old ones not in DEFAULT_USERS
    existing = load_data(USERS_FILE, {})
    # Remove old sales1 account if present, add benjamin
    if 'sales1' in existing:
        del existing['sales1']
    # Ensure all default users exist with correct names/roles
    for uname, udata in DEFAULT_USERS.items():
        if uname not in existing:
            existing[uname] = udata
        else:
            # Update name and role but keep custom password if set
            existing[uname]['name'] = udata['name']
            existing[uname]['role'] = udata['role']
    save_data(USERS_FILE, existing)

# ── Routes ─────────────────────────────────────────────────────────────────
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

@app.route('/login', methods=['POST'])
def login():
    users = load_data(USERS_FILE, DEFAULT_USERS)
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '')

    if username in users and users[username]['password'] == password:
        session['username']  = username
        session['role']      = users[username]['role']
        session['user_name'] = users[username]['name']
        return jsonify({'success': True, 'role': session['role'], 'name': session['user_name']})
    return jsonify({'success': False, 'error': 'Invalid username or password'})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'success': True})

# ── Get all data ───────────────────────────────────────────────────────────
@app.route('/api/get_data')
def get_data():
    if not logged_in():
        return jsonify({'error': 'Not logged in'}), 401

    deliveries = load_data(DELIVERIES_FILE, [])
    revenues   = load_data(REVENUES_FILE, [])
    expenses   = load_data(EXPENSES_FILE, [])
    moulds     = load_data(MOULDS_FILE, [])

    inventory = {}
    for bt in BLOCK_SIZES:
        delivered = sum(d['quantity'] for d in deliveries if d.get('size') == bt)
        moulded   = sum(m.get('total_blocks', 0) for m in moulds if m.get('size') == bt)
        inventory[bt] = {
            'delivered': delivered,
            'moulded':   moulded,
            'remaining': moulded - delivered
        }

    total_rev = sum(r.get('amount', 0) for r in revenues)
    total_exp = sum(e.get('amount', 0) for e in expenses)

    return jsonify({
        'user_name':   session.get('user_name'),
        'role':        session.get('role'),
        'deliveries':  deliveries[-200:],
        'revenues':    revenues[-200:],
        'expenses':    expenses[-200:],
        'moulds':      moulds[-200:],
        'inventory':   inventory,
        'stats': {
            'total_received': total_rev,
            'total_expenses': total_exp,
            'net_profit':     total_rev - total_exp
        }
    })

# ── Add operations ─────────────────────────────────────────────────────────
@app.route('/api/add_delivery', methods=['POST'])
def add_delivery():
    if not logged_in():
        return jsonify({'success': False, 'error': 'Not logged in'})
    data = request.json
    deliveries = load_data(DELIVERIES_FILE, [])
    deliveries.append({
        'date':     today_str(),
        'customer': data.get('customer'),
        'contact':  data.get('contact', ''),
        'size':     data.get('size'),
        'quantity': data.get('quantity'),
        'location': data.get('location', ''),
        'by':       session['username']
    })
    save_data(DELIVERIES_FILE, deliveries)
    return jsonify({'success': True})

@app.route('/api/add_revenue', methods=['POST'])
def add_revenue():
    if not logged_in():
        return jsonify({'success': False})
    data = request.json
    revenues = load_data(REVENUES_FILE, [])
    if data.get('type') == 'Blocks Sale':
        rec = {
            'date':     today_str(),
            'type':     'Blocks Sale',
            'size':     data.get('size'),
            'quantity': data.get('quantity', 0),
            'amount':   data.get('amount', 0),
            'desc':     '',
            'by':       session['username']
        }
    else:
        rec = {
            'date':     today_str(),
            'type':     'Other Income',
            'size':     '',
            'quantity': 0,
            'amount':   data.get('amount', 0),
            'desc':     data.get('description', ''),
            'by':       session['username']
        }
    revenues.append(rec)
    save_data(REVENUES_FILE, revenues)
    return jsonify({'success': True})

@app.route('/api/add_expense', methods=['POST'])
def add_expense():
    if not logged_in():
        return jsonify({'success': False})
    data = request.json
    expenses = load_data(EXPENSES_FILE, [])
    etype  = data.get('type')
    blocks = data.get('blocks', 0)
    if etype == 'Loading':
        desc = f"Loading – {blocks} blocks" if blocks else "Loading"
    elif etype == 'Other':
        desc = data.get('description', 'Other Expense')
    else:
        desc = "Diesel"
    expenses.append({
        'date':     today_str(),
        'category': etype,
        'desc':     desc,
        'blocks':   blocks,
        'amount':   data.get('amount'),
        'by':       session['username']
    })
    save_data(EXPENSES_FILE, expenses)
    return jsonify({'success': True})

@app.route('/api/add_mould', methods=['POST'])
def add_mould():
    if not logged_in():
        return jsonify({'success': False})
    data    = request.json
    moulds  = load_data(MOULDS_FILE, [])
    size    = data.get('size')
    palettes = data.get('palettes')
    bpp     = 6 if '5' in size else 5
    total_blocks = palettes * bpp
    moulds.append({
        'date':         today_str(),
        'size':         size,
        'palettes':     palettes,
        'total_blocks': total_blocks,
        'cement':       data.get('cement'),
        'by':           session['username']
    })
    save_data(MOULDS_FILE, moulds)
    return jsonify({'success': True})

# ── Delete operations — System Admin only ──────────────────────────────────
@app.route('/api/delete_delivery', methods=['POST'])
def delete_delivery():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data       = request.json
    deliveries = load_data(DELIVERIES_FILE, [])
    idx        = data.get('index')
    if idx is not None and 0 <= idx < len(deliveries):
        deliveries.pop(idx)
        save_data(DELIVERIES_FILE, deliveries)
    return jsonify({'success': True})

@app.route('/api/delete_revenue', methods=['POST'])
def delete_revenue():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data     = request.json
    revenues = load_data(REVENUES_FILE, [])
    idx      = data.get('index')
    if idx is not None and 0 <= idx < len(revenues):
        revenues.pop(idx)
        save_data(REVENUES_FILE, revenues)
    return jsonify({'success': True})

@app.route('/api/delete_expense', methods=['POST'])
def delete_expense():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data     = request.json
    expenses = load_data(EXPENSES_FILE, [])
    idx      = data.get('index')
    if idx is not None and 0 <= idx < len(expenses):
        expenses.pop(idx)
        save_data(EXPENSES_FILE, expenses)
    return jsonify({'success': True})

@app.route('/api/delete_mould', methods=['POST'])
def delete_mould():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data   = request.json
    moulds = load_data(MOULDS_FILE, [])
    idx    = data.get('index')
    if idx is not None and 0 <= idx < len(moulds):
        moulds.pop(idx)
        save_data(MOULDS_FILE, moulds)
    return jsonify({'success': True})

# ── User management — System Admin only ───────────────────────────────────
@app.route('/api/get_users')
def get_users():
    if not is_system_admin():
        return jsonify({'error': 'System Administrator only'}), 403
    users = load_data(USERS_FILE, DEFAULT_USERS)
    safe  = {u: {'name': v['name'], 'role': v['role']} for u, v in users.items()}
    return jsonify(safe)

@app.route('/api/update_user', methods=['POST'])
def update_user():
    if not is_system_admin():
        return jsonify({'success': False, 'error': 'System Administrator only'})
    data  = request.json
    users = load_data(USERS_FILE, DEFAULT_USERS)
    uname = data.get('username')
    if uname in users:
        if data.get('password'):
            users[uname]['password'] = data['password']
        if data.get('name'):
            users[uname]['name'] = data['name']
        if data.get('role'):
            users[uname]['role'] = data['role']
        save_data(USERS_FILE, users)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'User not found'})

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
    print("\n  👤 SYSTEM ADMINISTRATOR")
    print("     Username : sylvester")
    print("     Password : osei17")
    print("\n  👤 MANAGER")
    print("     Username : nanapoku")
    print("     Password : patcus17")
    print("\n  👤 SALES")
    print("     Username : benjamin")
    print("     Password : benji45")
    print("\n  📲 Install as PWA:")
    print("     1. Open URL on phone")
    print("     2. Tap menu → 'Add to Home Screen'")
    print("="*55 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
