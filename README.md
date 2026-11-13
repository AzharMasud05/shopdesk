# ShopDesk — Shop Inventory Management System

A bilingual (Bangla + English) Flask/SQLite starter application for a clothing shop.

## Features included
- Admin, Manager and Salesman login roles
- Product catalogue: unique product code, category, size, color, purchase price and selling price
- Godown and Showroom stock balances
- Manual stock additions
- Godown ↔ Showroom stock transfer with insufficient-stock validation and movement history
- Sales from showroom stock, invoice IDs, payment method and partial payment field
- Cash ledger for income and expenses
- Dashboard, low-stock list, daily sales and gross-profit reports
- Admin activity log
- Barcode scanner support: common USB scanners act as keyboard input; scan the product code into the code field
- Barcode labels show product code text; use a barcode label printer / barcode-generation add-on for printed machine-readable labels

## Run locally
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Initial login:
- Username: `admin`
- Password: `Admin@123`

**Immediately change the default password before using real shop data.** This starter currently has no password-change screen; change it in the SQLite `users` table using a small admin script or add a password-change feature before deployment.

## Important production notes
This is a working local starter, not yet a hardened public multi-branch production deployment. For real concurrent remote users, deploy behind HTTPS with a production WSGI server, set a long random `SECRET_KEY`, configure automated database backups, add CSRF protection, password reset/change, stronger validation, and test restore procedures. SQLite is suitable for a small single-server shop; for heavier simultaneous use, migrate to PostgreSQL.

## Current scope / accounting notes
- Sales reduce showroom stock.
- Sales paid amount is recorded as cash-ledger income. Unpaid balance is visible as total minus paid on the invoice record, but a full customer receivables/payment collection module is not yet implemented.
- Gross profit report uses sold quantity × (unit selling price − saved purchase cost).
- Purchase supplier ledger, returns/refunds, multi-item cart invoices, tax/VAT, barcode printing and stock adjustment approval are future extensions.

---

## মোবাইল ও পিসি থেকে চালানো (Run on Mobile & PC)

অ্যাপটি একই WiFi-এ মোবাইল ও পিসি উভয়েই চলে। দুটি উপায় আছে:

### উপায় ১: পিসিতে লোকালি রান (একই WiFi-এ মোবাইলের জন্য)

১. `start.bat` ফাইলটিতে ডবল-ক্লিক করুন (অথবা টার্মিনালে `python app.py` চালান)।
২. পিসিতে খুলুন: `http://127.0.0.1:5000`
৩. মোবাইল থেকে খুলুন: `http://<পিসির-আইপি-অ্যাড্রেস>:5000`
   - উদাহরণ: `http://192.168.1.5:5000`
   - পিসির আইপি জানতে কমান্ড প্রম্পটে `ipconfig` টাইপ করে "IPv4 Address" দেখুন।
৪. মোবাইল এবং পিসি অবশ্যই একই WiFi নেটওয়ার্কে থাকতে হবে।

লগইন:username `admin`, পাসওয়ার্ড `Admin@123` (ব্যবহার আগে পাসওয়ার্ড বদল করার অনুরোধ)。

### উপায় ২: সর্বদা খোলার জন্য পাবলিক লিঙ্ক (কোন জায়গা থেকে মোবাইল/পিসি)

আপনি শুধু একটি নাম বা লিঙ্ক দিয়ে মোবাইল ও পিসি থেকে ব্যবহার করতে চাইলে, রেন্ডার (Render) বা রেলওয়ে (Railway)য় বিনামূল্যে ডেপ্লয় করুন:

১. কোডটি গাইথাব (GitHub) রেপোজিটরিতে পুশ করুন।
২. [render.com](https://render.com) অথবা [railway.app](https://railway.app)-এ অ্যাকাউন্ট খুলে "New Web Service" বাটনে ক্লিক করুন গাইথাব রেপোর নাম দিয়ে।
৩. বিল্ড কমান্ড: `pip install -r requirements.txt`
   স্টার্ট কমান্ড: `python app.py`
৪. ডেপ্লয় হয়ে গেলে রেন্ডার একটি লিঙ্ক দেবে (যেমন: `https://shopdesk-inventory.onrender.com`)। এই লিঙ্কটি যেকোনো মোবাইল বা পিসি থেকে খোলা যাবে।

সতর্কতা: এটি ছোট দোকানের জন্য স্টার্টার এপ্লিকেশন। বাস্তব দোকান ডেটার জন্য HTTPS, শক্তিশালী SECRET_KEY, ডাটাবেস ব্যাকআপ এবং পাসওয়ার্ড পরিবর্তন স্ক্রীন যোগ করার পর ব্যবহার করুন।

