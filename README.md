# 🔥 The Golden Lantern — Flask + SQLite Restaurant App

A full-stack restaurant ordering web app built with Python/Flask and SQLite. No external database required — everything runs from a single `.db` file.

---

## ✨ Features

### Customers
- Browse menu (Breakfast, Lunch, Dinner, Desserts, Drinks)
- Guest ordering or create an account
- Shopping cart with quantity controls
- Payment (Credit Card, Apple Pay, Cash) + tip selector
- Order confirmation with receipt & estimated wait time
- **"See you soon!"** logo on confirmation screen
- Order history page (signed-in customers)
- Star ratings + written reviews
- Profile management (update name, email, password)
- Simulated confirmation email with review link

### Owner (login: `abs` / `123456`)
- Dashboard with live order stats + revenue
- Update order status: Not Started → In Progress → Ready → Delivered (no page reload)
- Menu manager: add, edit, delete dishes by section
- View simulated email log
- Owner profile: update name, email, avatar, username & password

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

The SQLite database is created automatically at `instance/golden_lantern.db` on first run.

---

## 📁 Project Structure

```
golden-lantern-flask/
├── app.py                  # Flask app, all routes, SQLite logic
├── requirements.txt
├── README.md
├── instance/
│   └── golden_lantern.db   # Auto-created SQLite database
├── templates/
│   ├── base.html           # Shared nav, flash messages, footer
│   ├── index.html          # Home page
│   ├── menu.html           # Menu with sections
│   ├── cart.html           # Shopping cart
│   ├── payment.html        # Payment + tip
│   ├── confirm.html        # Order confirmation + logo
│   ├── login.html          # Customer & owner login
│   ├── register.html       # Customer registration
│   ├── orders.html         # Customer order history
│   ├── profile.html        # Customer profile settings
│   ├── reviews.html        # Reviews page
│   ├── dashboard.html      # Owner order dashboard
│   ├── admin_menu.html     # Owner menu manager
│   ├── menu_form.html      # Add/edit dish form
│   ├── owner_profile.html  # Owner profile & credentials
│   └── owner_emails.html   # Simulated email log
└── static/
    ├── css/styles.css
    └── js/main.js
```

---

## 📧 Real Email Setup

By default, emails are **simulated** (stored in the database and viewable in the owner's Email Log). To send real emails:

1. Open `app.py`
2. Find `EMAIL_CONFIG` near the top
3. Fill in your credentials and set `'enabled': True`

```python
EMAIL_CONFIG = {
    'enabled': True,
    'host':    'smtp.gmail.com',
    'port':    587,
    'user':    'your@gmail.com',
    'pass':    'your_app_password',   # Gmail App Password (not your login password)
    'from':    'The Golden Lantern <your@gmail.com>',
}
```

**Recommended email services:** Resend, SendGrid, Mailgun, or Gmail with an App Password.

---

## ☁️ Deploy to the Web

Flask apps **cannot** run on GitHub Pages (static only). Use one of these instead:

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| [Railway](https://railway.app) | ✅ | Push GitHub repo, auto-deploys |
| [Render](https://render.com) | ✅ | Easy Flask support |
| [PythonAnywhere](https://pythonanywhere.com) | ✅ | Built for Python/Flask |
| [Fly.io](https://fly.io) | ✅ | Docker-based, very fast |

### Deploy to Railway (easiest)
1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set start command: `python app.py`
4. Done — live URL in ~2 minutes

### Deploy to Render
1. Push to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`

---

## 🗄️ Database

All data is stored in SQLite (`instance/golden_lantern.db`):

| Table | Contents |
|-------|----------|
| `owner` | Owner credentials & profile |
| `customers` | Customer accounts |
| `menu` | All dishes |
| `orders` | All placed orders |
| `order_items` | Line items per order |
| `reviews` | Customer reviews & ratings |
| `sim_emails` | Simulated email log |

---

## 🔐 Default Credentials

| Role | Username / Email | Password |
|------|-----------------|----------|
| Owner | `abs` | `123456` |

Change these in **Owner Profile** after first login.

---

*The Golden Lantern — Where every plate tells a story. 🔥*
