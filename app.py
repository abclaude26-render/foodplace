"""
The Golden Lantern — Flask + SQLite Restaurant App
Run:  python app.py
"""

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, g)
import sqlite3, os, hashlib, secrets, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATABASE = os.path.join(os.path.dirname(__file__), 'instance', 'golden_lantern.db')

# ── Email config (update with real credentials or use Gmail App Password) ────
EMAIL_CONFIG = {
    'enabled': False,           # Set True to send real emails
    'host':    'smtp.gmail.com',
    'port':    587,
    'user':    'your@gmail.com',
    'pass':    'your_app_password',
    'from':    'The Golden Lantern <your@gmail.com>',
}

# ── Database ─────────────────────────────────────────────────────────────────
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def execute_db(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
    CREATE TABLE IF NOT EXISTS owner (
        id       INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name     TEXT DEFAULT 'Owner',
        email    TEXT DEFAULT '',
        avatar   TEXT DEFAULT '🔥',
        created  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS customers (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT NOT NULL,
        email    TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        joined   TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS menu (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT NOT NULL,
        name    TEXT NOT NULL,
        desc    TEXT DEFAULT '',
        price   REAL NOT NULL,
        emoji   TEXT DEFAULT '🍽️',
        active  INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        order_ref     TEXT UNIQUE NOT NULL,
        customer_id   INTEGER,
        customer_name TEXT NOT NULL,
        customer_email TEXT DEFAULT '',
        status        TEXT DEFAULT 'Not Started',
        pay_method    TEXT DEFAULT 'card',
        subtotal      REAL DEFAULT 0,
        tax           REAL DEFAULT 0,
        tip           REAL DEFAULT 0,
        tip_pct       INTEGER DEFAULT 0,
        total         REAL DEFAULT 0,
        wait_minutes  INTEGER DEFAULT 15,
        placed_at     TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id  INTEGER NOT NULL,
        menu_id   INTEGER NOT NULL,
        name      TEXT NOT NULL,
        emoji     TEXT DEFAULT '🍽️',
        price     REAL NOT NULL,
        qty       INTEGER NOT NULL,
        subtotal  REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        name      TEXT NOT NULL,
        email     TEXT DEFAULT '',
        rating    INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        body      TEXT NOT NULL,
        created   TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sim_emails (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        to_addr   TEXT NOT NULL,
        subject   TEXT NOT NULL,
        body      TEXT NOT NULL,
        order_ref TEXT,
        sent_at   TEXT DEFAULT (datetime('now'))
    );
    """)

    # Default owner
    row = db.execute("SELECT id FROM owner WHERE id=1").fetchone()
    if not row:
        db.execute("INSERT INTO owner (id,username,password,name,email,avatar) VALUES (1,?,?,?,?,?)",
                   ('abs', hash_pw('123456'), 'Owner', 'owner@goldenlantern.com', '🔥'))

    # Default menu
    if not db.execute("SELECT id FROM menu LIMIT 1").fetchone():
        dishes = [
            ('Breakfast','Smokehouse Biscuit Sandwich','Fluffy buttermilk biscuit with smoked sausage, fried egg & cheddar',10.00,'🥚'),
            ('Breakfast','BBQ Bacon Skillet','Hickory bacon, home fries, peppers & onions topped with two eggs',12.50,'🍳'),
            ('Breakfast','Pitmaster Pancakes','Thick buttermilk stack with maple butter & candied bacon crumbles',11.00,'🥞'),
            ('Breakfast','Country Gravy & Biscuits','Two flaky biscuits smothered in house-made sausage gravy',9.00,'🫙'),
            ('Lunch','Pulled Pork Sandwich','Slow-smoked pulled pork on a brioche bun with coleslaw & pickles',13.50,'🥪'),
            ('Lunch','BBQ Chicken Wrap','Smoked chicken, roasted corn, black beans, cheddar & chipotle ranch',12.00,'🌯'),
            ('Lunch','Smoked Brisket Tacos','Three flour tortillas with sliced brisket, pico & avocado crema',14.00,'🌮'),
            ('Lunch','Classic Burger','Half-pound beef patty, American cheese, lettuce, tomato & secret sauce',13.00,'🍔'),
            ('Dinner','Full Rack of Ribs','St. Louis-style baby back ribs with house dry rub & signature BBQ sauce',36.00,'🍖'),
            ('Dinner','Smoked Beef Brisket','12-hour oak-smoked brisket sliced to order, served with two sides',28.00,'🥩'),
            ('Dinner','BBQ Chicken Platter','Half smoked chicken with crispy skin, served with cornbread & slaw',22.00,'🍗'),
            ('Dinner','Pitmaster Sampler','Brisket, ribs, pulled pork & smoked sausage with two sides',42.00,'🍽️'),
            ('Desserts','Peach Cobbler','Warm Georgia peach cobbler topped with a scoop of vanilla ice cream',7.50,'🍑'),
            ('Desserts','Banana Pudding','Layers of vanilla wafers, banana slices & homemade whipped pudding',6.50,'🍌'),
            ('Desserts','Brownie Skillet','Warm dark chocolate brownie in a cast-iron skillet with ice cream & caramel',8.50,'🍫'),
            ('Desserts','Sweet Potato Pie','Classic Southern-spiced pie with cinnamon whipped cream',6.00,'🥧'),
            ('Drinks','Fresh Lemonade','Freshly squeezed with a hint of mint, served over crushed ice',3.50,'🍋'),
            ('Drinks','Sweet Tea','House-brewed Southern sweet tea, bottomless refills',3.00,'🧊'),
            ('Drinks','Craft Root Beer','Local small-batch root beer, served in a frosty mug',4.50,'🍺'),
            ('Drinks','Watermelon Limeade','Fresh watermelon juice blended with tart lime & sparkling water',5.00,'🍉'),
        ]
        db.executemany("INSERT INTO menu (section,name,desc,price,emoji) VALUES (?,?,?,?,?)", dishes)

    db.commit()
    db.close()
    print("✓ Database initialized:", DATABASE)

# ── Auth decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('customer_id') and not session.get('owner'):
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('owner'):
            flash('Owner access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('customer_id'):
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Email helper ──────────────────────────────────────────────────────────────
def send_email(to_addr, subject, body, order_ref=None):
    """Store simulated email always. Send real email if config enabled."""
    execute_db("INSERT INTO sim_emails (to_addr,subject,body,order_ref) VALUES (?,?,?,?)",
               (to_addr, subject, body, order_ref))
    if EMAIL_CONFIG['enabled']:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = EMAIL_CONFIG['from']
            msg['To']      = to_addr
            msg.attach(MIMEText(body, 'plain'))
            with smtplib.SMTP(EMAIL_CONFIG['host'], EMAIL_CONFIG['port']) as srv:
                srv.starttls()
                srv.login(EMAIL_CONFIG['user'], EMAIL_CONFIG['pass'])
                srv.sendmail(EMAIL_CONFIG['user'], to_addr, msg.as_string())
        except Exception as e:
            print(f"Email send error: {e}")

def build_confirm_email(order, items, review_url):
    lines = [f"Hi {order['customer_name']},",
             "",
             "Thank you for your order at The Golden Lantern!",
             f"Order #{order['order_ref']}",
             "",
             "Items ordered:"]
    for it in items:
        lines.append(f"  {it['emoji']} {it['name']} x{it['qty']}  ${it['subtotal']:.2f}")
    lines += ["",
              f"Subtotal : ${order['subtotal']:.2f}",
              f"Tax      : ${order['tax']:.2f}",
              f"Tip      : ${order['tip']:.2f}",
              f"Total    : ${order['total']:.2f}",
              "",
              f"Estimated wait: {order['wait_minutes']} minutes",
              "",
              f"⭐ Leave a review: {review_url}",
              "",
              "See you soon!",
              "— The Golden Lantern Team"]
    return "\n".join(lines)

# ── Context processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    cart = session.get('cart', {})
    cart_count = sum(cart.values())
    return dict(
        cart_count=cart_count,
        is_owner=session.get('owner', False),
        customer_id=session.get('customer_id'),
        customer_name=session.get('customer_name', ''),
        sections=['Breakfast','Lunch','Dinner','Desserts','Drinks'],
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTES — PUBLIC
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    reviews = query_db("SELECT * FROM reviews ORDER BY created DESC LIMIT 3")
    avg = query_db("SELECT AVG(rating) as avg FROM reviews", one=True)
    avg_rating = round(avg['avg'], 1) if avg and avg['avg'] else None
    return render_template('index.html', reviews=reviews, avg_rating=avg_rating)

@app.route('/menu')
def menu():
    section = request.args.get('section', 'Breakfast')
    items   = query_db("SELECT * FROM menu WHERE section=? AND active=1", (section,))
    cart    = session.get('cart', {})
    return render_template('menu.html', items=items, section=section, cart=cart)

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    if not cart:
        return render_template('cart.html', items=[], sub=0, tax=0, total=0)
    ids = list(cart.keys())
    placeholders = ','.join('?' * len(ids))
    menu_items = query_db(f"SELECT * FROM menu WHERE id IN ({placeholders})", ids)
    items = []
    sub = 0
    for m in menu_items:
        q = int(cart.get(str(m['id']), 0))
        if q > 0:
            line = q * m['price']
            items.append({**dict(m), 'qty': q, 'line_total': line})
            sub += line
    tax   = round(sub * 0.0875, 2)
    total = round(sub + tax, 2)
    return render_template('cart.html', items=items,
                           sub=round(sub,2), tax=tax, total=total)

@app.route('/cart/add/<int:item_id>', methods=['POST'])
def cart_add(item_id):
    cart = session.get('cart', {})
    key  = str(item_id)
    cart[key] = cart.get(key, 0) + 1
    session['cart'] = cart
    return redirect(request.referrer or url_for('menu'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def cart_remove(item_id):
    cart = session.get('cart', {})
    key  = str(item_id)
    if key in cart:
        cart[key] = max(0, cart[key] - 1)
        if cart[key] == 0:
            del cart[key]
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart/delete/<int:item_id>', methods=['POST'])
def cart_delete(item_id):
    cart = session.get('cart', {})
    cart.pop(str(item_id), None)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/payment', methods=['GET','POST'])
def payment():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('menu'))

    ids = list(cart.keys())
    placeholders = ','.join('?' * len(ids))
    menu_items = query_db(f"SELECT * FROM menu WHERE id IN ({placeholders})", ids)

    items, sub = [], 0
    for m in menu_items:
        q = int(cart.get(str(m['id']), 0))
        if q > 0:
            line = round(q * m['price'], 2)
            items.append({**dict(m), 'qty': q, 'line_total': line})
            sub += line
    sub   = round(sub, 2)
    tax   = round(sub * 0.0875, 2)

    if request.method == 'POST':
        pay_method  = request.form.get('pay_method', 'card')
        tip_pct     = int(request.form.get('tip_pct', 15))
        guest_name  = request.form.get('guest_name', '').strip()
        guest_email = request.form.get('guest_email', '').strip()

        tip   = round(sub * tip_pct / 100, 2)
        total = round(sub + tax + tip, 2)
        wait  = __import__('random').randint(10, 25)

        # Determine customer info
        cust_id    = session.get('customer_id')
        cust_name  = session.get('customer_name', guest_name or 'Guest')
        cust_email = session.get('customer_email', guest_email or '')

        if not cust_id and not guest_name:
            flash('Please enter your name to continue.', 'danger')
            return render_template('payment.html', items=items, sub=sub, tax=tax)

        # Create order
        import random
        order_ref = 'GL-' + ''.join(random.choices('0123456789ABCDEF', k=8))
        order_id  = execute_db("""
            INSERT INTO orders (order_ref,customer_id,customer_name,customer_email,
                pay_method,subtotal,tax,tip,tip_pct,total,wait_minutes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (order_ref, cust_id, cust_name, cust_email,
             pay_method, sub, tax, tip, tip_pct, total, wait))

        for it in items:
            execute_db("""INSERT INTO order_items (order_id,menu_id,name,emoji,price,qty,subtotal)
                          VALUES (?,?,?,?,?,?,?)""",
                       (order_id, it['id'], it['name'], it['emoji'],
                        it['price'], it['qty'], it['line_total']))

        session['cart'] = {}
        session['last_order_ref'] = order_ref

        # Send email
        if cust_email:
            order_row = query_db("SELECT * FROM orders WHERE id=?", (order_id,), one=True)
            review_url = request.host_url.rstrip('/') + url_for('reviews') + '?order=' + order_ref
            body = build_confirm_email(order_row, items, review_url)
            send_email(cust_email,
                       f"Your Golden Lantern Order is Confirmed! ({order_ref})",
                       body, order_ref)

        return redirect(url_for('confirm'))

    return render_template('payment.html', items=items, sub=sub, tax=tax)

@app.route('/confirm')
def confirm():
    order_ref = session.get('last_order_ref')
    if not order_ref:
        return redirect(url_for('index'))
    order = query_db("SELECT * FROM orders WHERE order_ref=?", (order_ref,), one=True)
    items = query_db("SELECT * FROM order_items WHERE order_id=?", (order['id'],))
    email_log = query_db("SELECT * FROM sim_emails WHERE order_ref=? ORDER BY sent_at DESC LIMIT 1",
                         (order_ref,), one=True)
    return render_template('confirm.html', order=order, items=items, email_log=email_log)

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        mode = request.form.get('mode')

        if mode == 'owner':
            owner = query_db("SELECT * FROM owner WHERE id=1", one=True)
            if (owner and request.form['username'] == owner['username']
                    and hash_pw(request.form['password']) == owner['password']):
                session['owner'] = True
                session['owner_name'] = owner['name']
                return redirect(url_for('dashboard'))
            flash('Invalid owner credentials.', 'danger')

        elif mode == 'customer':
            email = request.form['email'].strip().lower()
            pw    = request.form['password']
            cust  = query_db("SELECT * FROM customers WHERE LOWER(email)=?", (email,), one=True)
            if cust and hash_pw(pw) == cust['password']:
                session['customer_id']    = cust['id']
                session['customer_name']  = cust['name']
                session['customer_email'] = cust['email']
                return redirect(url_for('menu'))
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name  = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        pw    = request.form['password']
        if not name or not email or not pw:
            flash('Please fill in all fields.', 'danger')
        elif query_db("SELECT id FROM customers WHERE LOWER(email)=?", (email,), one=True):
            flash('That email is already registered.', 'danger')
        else:
            cid = execute_db("INSERT INTO customers (name,email,password) VALUES (?,?,?)",
                             (name, email, hash_pw(pw)))
            session['customer_id']    = cid
            session['customer_name']  = name
            session['customer_email'] = email
            flash('Welcome! Your account has been created.', 'success')
            return redirect(url_for('menu'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── Customer pages ────────────────────────────────────────────────────────────
@app.route('/orders')
@customer_required
def orders():
    cust_orders = query_db(
        "SELECT * FROM orders WHERE customer_id=? ORDER BY placed_at DESC",
        (session['customer_id'],))
    order_items_map = {}
    for o in cust_orders:
        order_items_map[o['id']] = query_db(
            "SELECT * FROM order_items WHERE order_id=?", (o['id'],))
    return render_template('orders.html', orders=cust_orders,
                           order_items_map=order_items_map)

@app.route('/profile', methods=['GET','POST'])
@customer_required
def profile():
    cust = query_db("SELECT * FROM customers WHERE id=?",
                    (session['customer_id'],), one=True)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_info':
            name  = request.form['name'].strip()
            email = request.form['email'].strip().lower()
            if not name or not email:
                flash('Name and email are required.', 'danger')
            else:
                execute_db("UPDATE customers SET name=?,email=? WHERE id=?",
                           (name, email, cust['id']))
                session['customer_name']  = name
                session['customer_email'] = email
                flash('Profile updated!', 'success')
                return redirect(url_for('profile'))
        elif action == 'change_password':
            old = request.form['old_password']
            new = request.form['new_password']
            if hash_pw(old) != cust['password']:
                flash('Current password is incorrect.', 'danger')
            elif len(new) < 4:
                flash('New password must be at least 4 characters.', 'danger')
            else:
                execute_db("UPDATE customers SET password=? WHERE id=?",
                           (hash_pw(new), cust['id']))
                flash('Password updated!', 'success')
                return redirect(url_for('profile'))
    return render_template('profile.html', cust=cust)

# ── Reviews ───────────────────────────────────────────────────────────────────
@app.route('/reviews', methods=['GET','POST'])
def reviews():
    if request.method == 'POST':
        if not session.get('customer_id'):
            flash('Please sign in to leave a review.', 'warning')
            return redirect(url_for('login'))
        rating = int(request.form.get('rating', 0))
        body   = request.form.get('body', '').strip()
        if not rating or not body:
            flash('Please provide a rating and review text.', 'danger')
        else:
            execute_db("""INSERT INTO reviews (customer_id,name,email,rating,body)
                          VALUES (?,?,?,?,?)""",
                       (session['customer_id'], session['customer_name'],
                        session.get('customer_email',''), rating, body))
            flash('Thank you for your review!', 'success')
            return redirect(url_for('reviews'))

    all_reviews = query_db("SELECT * FROM reviews ORDER BY created DESC")
    avg = query_db("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews", one=True)
    order_ref = request.args.get('order')
    return render_template('reviews.html', reviews=all_reviews, avg=avg,
                           order_ref=order_ref)

# ═══════════════════════════════════════════════════════════════════════════════
#  OWNER ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/owner/dashboard')
@owner_required
def dashboard():
    all_orders = query_db("SELECT * FROM orders ORDER BY placed_at DESC")
    order_items_map = {}
    for o in all_orders:
        order_items_map[o['id']] = query_db(
            "SELECT * FROM order_items WHERE order_id=?", (o['id'],))
    stats = {
        'total':       len(all_orders),
        'not_started': sum(1 for o in all_orders if o['status']=='Not Started'),
        'in_progress': sum(1 for o in all_orders if o['status']=='In Progress'),
        'ready':       sum(1 for o in all_orders if o['status']=='Ready'),
        'delivered':   sum(1 for o in all_orders if o['status']=='Delivered'),
        'revenue':     sum(o['total'] for o in all_orders),
    }
    return render_template('dashboard.html', orders=all_orders,
                           order_items_map=order_items_map, stats=stats)

@app.route('/owner/order/<int:order_id>/status', methods=['POST'])
@owner_required
def update_order_status(order_id):
    status = request.form.get('status')
    allowed = ['Not Started','In Progress','Ready','Delivered']
    if status in allowed:
        execute_db("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    return redirect(url_for('dashboard') + f'#order-{order_id}')

@app.route('/owner/menu')
@owner_required
def admin_menu():
    section = request.args.get('section', 'All')
    if section == 'All':
        items = query_db("SELECT * FROM menu ORDER BY section,id")
    else:
        items = query_db("SELECT * FROM menu WHERE section=? ORDER BY id", (section,))
    return render_template('admin_menu.html', items=items, section=section)

@app.route('/owner/menu/add', methods=['GET','POST'])
@owner_required
def menu_add():
    if request.method == 'POST':
        section = request.form['section']
        name    = request.form['name'].strip()
        desc    = request.form['desc'].strip()
        price   = float(request.form['price'])
        emoji   = request.form['emoji'].strip() or '🍽️'
        execute_db("INSERT INTO menu (section,name,desc,price,emoji) VALUES (?,?,?,?,?)",
                   (section, name, desc, price, emoji))
        flash(f'"{name}" added to {section}.', 'success')
        return redirect(url_for('admin_menu'))
    return render_template('menu_form.html', dish=None, action='Add')

@app.route('/owner/menu/edit/<int:dish_id>', methods=['GET','POST'])
@owner_required
def menu_edit(dish_id):
    dish = query_db("SELECT * FROM menu WHERE id=?", (dish_id,), one=True)
    if not dish:
        flash('Dish not found.', 'danger')
        return redirect(url_for('admin_menu'))
    if request.method == 'POST':
        execute_db("""UPDATE menu SET section=?,name=?,desc=?,price=?,emoji=?
                      WHERE id=?""",
                   (request.form['section'], request.form['name'].strip(),
                    request.form['desc'].strip(), float(request.form['price']),
                    request.form['emoji'].strip() or '🍽️', dish_id))
        flash('Dish updated.', 'success')
        return redirect(url_for('admin_menu'))
    return render_template('menu_form.html', dish=dish, action='Edit')

@app.route('/owner/menu/delete/<int:dish_id>', methods=['POST'])
@owner_required
def menu_delete(dish_id):
    dish = query_db("SELECT name FROM menu WHERE id=?", (dish_id,), one=True)
    if dish:
        execute_db("DELETE FROM menu WHERE id=?", (dish_id,))
        flash(f'"{dish["name"]}" removed from menu.', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/owner/profile', methods=['GET','POST'])
@owner_required
def owner_profile():
    owner = query_db("SELECT * FROM owner WHERE id=1", one=True)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            execute_db("UPDATE owner SET name=?,email=?,avatar=? WHERE id=1",
                       (request.form['name'].strip(),
                        request.form['email'].strip(),
                        request.form['avatar'].strip() or '🔥'))
            session['owner_name'] = request.form['name'].strip()
            flash('Profile updated!', 'success')
        elif action == 'update_credentials':
            old = request.form['old_password']
            new_user = request.form['new_username'].strip()
            new_pass = request.form['new_password']
            if hash_pw(old) != owner['password']:
                flash('Current password is incorrect.', 'danger')
            elif not new_user or not new_pass:
                flash('Username and new password are required.', 'danger')
            else:
                execute_db("UPDATE owner SET username=?,password=? WHERE id=1",
                           (new_user, hash_pw(new_pass)))
                flash('Credentials updated! Please log in again.', 'success')
                session.clear()
                return redirect(url_for('login'))
        return redirect(url_for('owner_profile'))
    return render_template('owner_profile.html', owner=owner)

@app.route('/owner/reviews')
@owner_required
def owner_reviews():
    all_reviews = query_db("SELECT * FROM reviews ORDER BY created DESC")
    avg = query_db("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews", one=True)
    return render_template('reviews.html', reviews=all_reviews, avg=avg,
                           owner_view=True)

@app.route('/owner/emails')
@owner_required
def owner_emails():
    emails = query_db("SELECT * FROM sim_emails ORDER BY sent_at DESC LIMIT 50")
    return render_template('owner_emails.html', emails=emails)

# ── API: update order status via AJAX ────────────────────────────────────────
@app.route('/api/order/<int:order_id>/status', methods=['POST'])
@owner_required
def api_order_status(order_id):
    data   = request.get_json()
    status = data.get('status','')
    allowed = ['Not Started','In Progress','Ready','Delivered']
    if status in allowed:
        execute_db("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        return jsonify({'ok': True, 'status': status})
    return jsonify({'ok': False}), 400

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
