# -*- coding: utf-8 -*-
"""
POS UMKM BULO JAYA (Sembako & Kebutuhan Harian)
Jalankan:  streamlit run app.py
Fitur: Kasir (scan barcode / foto AI / pilih gambar), harga eceran-grosir otomatis,
stok otomatis berkurang, tambah-kurang stok (tombol cepat di galeri), pemantauan omset-modal-untung,
transaksi keuangan, struk, role Owner & Kasir.
Tambahan (gabungan app v2): keranjang tersimpan di database (aman mati lampu), SQLite WAL, barcode EAN-13 otomatis
untuk barang >= Rp5.000 + cetak barcode, 3 akun kasir awal.
Katalog: ±170 kebutuhan harian rumah tangga, foto kemasan asli diunduh otomatis dari internet.
"""
import os, io, re, json, html, base64, hashlib, hmac, secrets, sqlite3, time, shutil, threading, textwrap
import http.client, urllib.request, urllib.parse, urllib.error
import datetime as dt
from contextlib import closing
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DB = os.environ.get("POS_DB", "bulojaya_pos.db")
IMG_DIR = "gambar_produk"
os.makedirs(IMG_DIR, exist_ok=True)
TZ = dt.timezone(dt.timedelta(hours=8))  # WITA (Makassar)
HARGA_BARCODE_MIN = 5000  # barang dengan harga eceran >= ini otomatis dibuatkan barcode EAN-13

st.set_page_config(page_title="POS Bulo Jaya", page_icon="🛒", layout="wide")
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp [data-baseweb="tab"],.stApp [data-testid="stMetricValue"],.stApp [data-testid="stMetricLabel"]{font-family:'Poppins',system-ui,-apple-system,'Segoe UI',sans-serif}
.stApp{background:radial-gradient(900px 420px at 0% -5%,#dcfce7 0,rgba(220,252,231,0) 60%),radial-gradient(800px 380px at 100% 0%,#fef3c7 0,rgba(254,243,199,0) 55%),#f8fafc}
.block-container{padding-top:1.1rem;max-width:1450px}
footer,.stDeployButton{visibility:hidden}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(245,158,11,.6)}50%{box-shadow:0 0 0 7px rgba(245,158,11,0)}}
@keyframes scroll{to{transform:translateX(-100%)}}
/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{background:linear-gradient(185deg,#14532d 0%,#166534 55%,#15803d 100%)}
section[data-testid="stSidebar"] *{color:#ecfdf5}
.brand-side{display:flex;gap:12px;align-items:center;margin:4px 0 10px}
.brand-side .logo{font-size:1.9rem;background:rgba(255,255,255,.15);border-radius:14px;width:50px;height:50px;display:grid;place-items:center}
.brand-side .bn{font-weight:800;font-size:1.05rem;line-height:1.15;color:#fff}
.brand-side .bs{font-size:.74rem;color:#bbf7d0}
.userchip{background:rgba(255,255,255,.14);border-radius:12px;padding:8px 12px;font-size:.82rem;margin-bottom:14px}
section[data-testid="stSidebar"] [role="radiogroup"]{gap:6px}
section[data-testid="stSidebar"] label[data-baseweb="radio"]{background:rgba(255,255,255,.08);padding:10px 14px;border-radius:12px;width:100%;margin:0;transition:.15s}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover{background:rgba(255,255,255,.2);transform:translateX(3px)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]>div:nth-of-type(1){display:none}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked){background:#fff;box-shadow:0 6px 16px -6px rgba(0,0,0,.35)}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) *{color:#14532d;font-weight:700}
section[data-testid="stSidebar"] .stButton>button{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.3);color:#fff}
section[data-testid="stSidebar"] .stButton>button:hover{background:#fff;color:#14532d}
/* ---------- Header halaman & hero ---------- */
.phead{display:flex;align-items:center;gap:14px;background:#fff;border-radius:18px;padding:14px 20px;margin-bottom:14px;border:1px solid #e8f5e9;border-left:6px solid #16a34a;box-shadow:0 4px 18px -8px rgba(22,101,52,.25);animation:fadeUp .35s ease both}
.phead .ic{font-size:1.9rem;background:linear-gradient(135deg,#dcfce7,#fef9c3);border-radius:14px;width:54px;height:54px;display:grid;place-items:center}
.phead .tt{font-weight:800;font-size:1.35rem;color:#14532d;line-height:1.2}
.phead .ss{color:#64748b;font-size:.85rem}
.hero{background:linear-gradient(120deg,#14532d 0%,#16a34a 55%,#65a30d 100%);color:#fff;border-radius:22px;padding:22px 26px;position:relative;overflow:hidden;box-shadow:0 14px 34px -14px rgba(22,163,74,.7);margin-bottom:12px}
.hero:before,.hero:after{content:"";position:absolute;border-radius:50%;background:rgba(255,255,255,.09)}
.hero:before{width:240px;height:240px;right:-60px;top:-100px}
.hero:after{width:150px;height:150px;right:150px;bottom:-90px}
.hero .t{font-weight:800;font-size:1.55rem;line-height:1.2;position:relative;color:#fff}
.hero .s{color:#dcfce7;margin-top:2px;position:relative;font-size:.92rem}
.hero .wv{position:absolute;right:28px;top:14px;font-size:3.4rem;animation:float 3s ease-in-out infinite}
.hero .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;position:relative}
.hero .chip{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);padding:5px 13px;border-radius:999px;font-size:.8rem;font-weight:600;color:#fff}
.ticker{overflow:hidden;white-space:nowrap;background:#fffbeb;border:1px dashed #fbbf24;border-radius:12px;padding:8px 0;margin-bottom:14px}
.ticker .in{display:inline-block;padding-left:100%;animation:scroll 55s linear infinite;color:#92400e;font-weight:600;font-size:.85rem}
.ticker:hover .in{animation-play-state:paused}
.sech{font-weight:800;color:#14532d;font-size:1.1rem;margin:6px 0 10px}
.alertbar{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;border-radius:14px;padding:10px 14px;margin:4px 0 12px;font-size:.86rem}
/* ---------- Kartu produk ---------- */
[class*="st-key-pc_"],[class*="st-key-pg_"]{background:#fff;border-radius:18px;overflow:hidden;border:1px solid #e5e7eb;box-shadow:0 2px 10px rgba(15,23,42,.07);gap:0!important;transition:transform .18s,box-shadow .18s,border-color .18s;animation:fadeUp .35s ease both}
[class*="st-key-pc_"]:hover,[class*="st-key-pg_"]:hover{transform:translateY(-4px);box-shadow:0 16px 30px -14px rgba(22,163,74,.55);border-color:#86efac}
[class*="st-key-pc_"] [data-testid="stButton"]{padding:2px 12px 12px}
[class*="st-key-pg_"] [data-testid="stHorizontalBlock"]{padding:2px 12px 12px;gap:8px}
.pimg{position:relative;aspect-ratio:4/3;background:#fff;overflow:hidden}
.pimg img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .4s}
[class*="st-key-pc_"]:hover .pimg img,[class*="st-key-pg_"]:hover .pimg img{transform:scale(1.07)}
.pimg.out img{filter:grayscale(1);opacity:.5}
.tg{position:absolute;font-size:.68rem;font-weight:700;padding:3px 9px;border-radius:999px;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,.2)}
.tg.tl{top:8px;left:8px}.tg.tr{top:8px;right:8px}.tg.bl{bottom:8px;right:8px}
.tg.low{background:#f59e0b;animation:pulse 1.6s infinite}.tg.out{background:#ef4444}.tg.cart{background:#16a34a}.tg.kat{background:rgba(15,23,42,.62);font-weight:600}
.pbody{padding:10px 12px 8px}
.pbody .nm{font-weight:700;color:#111827;font-size:.9rem;line-height:1.25;min-height:2.5em;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pbody .pr{font-weight:800;color:#15803d;font-size:1.1rem;margin:2px 0}
.pbody .gr{font-size:.7rem;color:#b45309;background:#fef3c7;border-radius:8px;padding:2px 8px;display:inline-block;margin-bottom:7px}
.pbody .gr.none{background:transparent}
.sbar{height:7px;border-radius:99px;background:#e5e7eb;overflow:hidden}
.sbar i{display:block;height:100%;border-radius:99px}
.sinfo{display:flex;justify-content:space-between;font-size:.72rem;color:#64748b;margin-top:4px}
/* ---------- Chip kategori ---------- */
.st-key-cat_k [role="radiogroup"]{gap:8px;flex-wrap:wrap}
.st-key-cat_k label[data-baseweb="radio"]{background:#fff;border:1px solid #e5e7eb;border-radius:999px;padding:6px 15px;margin:0;transition:.15s}
.st-key-cat_k label[data-baseweb="radio"]:hover{border-color:#16a34a;transform:translateY(-1px)}
.st-key-cat_k label[data-baseweb="radio"]>div:nth-of-type(1){display:none}
.st-key-cat_k label[data-baseweb="radio"]:has(input:checked){background:#16a34a;border-color:#16a34a;box-shadow:0 6px 14px -6px rgba(22,163,74,.7)}
.st-key-cat_k label[data-baseweb="radio"]:has(input:checked) *{color:#fff;font-weight:700}
/* ---------- Keranjang ---------- */
.carttitle{font-weight:800;font-size:1.25rem;color:#14532d;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.carttitle .pill{background:#16a34a;color:#fff;border-radius:999px;font-size:.78rem;padding:2px 11px}
[class*="st-key-ci_"]{background:linear-gradient(180deg,#fff,#f7fee7);border:1px solid #d9f99d;border-radius:16px;padding:10px 12px;box-shadow:0 2px 8px rgba(15,23,42,.05);animation:fadeUp .25s ease both}
.cihead{display:flex;gap:10px;align-items:center}
.cihead img{width:52px;height:52px;border-radius:12px;object-fit:cover;box-shadow:0 2px 6px rgba(0,0,0,.18)}
.cihead .nm{font-weight:700;color:#111827;font-size:.92rem;line-height:1.2}
.cihead .sb{font-size:.74rem;color:#64748b}
.empty{text-align:center;padding:28px 12px;border:2px dashed #bbf7d0;border-radius:20px;background:#f0fdf4;color:#166534;font-weight:600}
.empty .big{font-size:3.4rem;animation:float 3s ease-in-out infinite}
.empty small{font-weight:400;color:#4d7c0f}
.badge-g{background:#16a34a;color:#fff;padding:2px 10px;border-radius:12px;font-weight:700;font-size:.78rem}
.badge-e{background:#e5e7eb;color:#374151;padding:2px 10px;border-radius:12px;font-size:.78rem}
.total{background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;border-radius:18px;padding:14px 20px;font-size:1.85rem;font-weight:800;display:flex;justify-content:space-between;align-items:center;box-shadow:0 12px 26px -14px rgba(15,23,42,.8);margin:6px 0}
.total small{font-size:.72rem;font-weight:600;color:#94a3b8;letter-spacing:.8px}
.total b{color:#4ade80;font-size:.95rem}
/* ---------- Peringkat terlaris ---------- */
.rank{background:#fff;border-radius:16px;border:1px solid #e5e7eb;padding:10px;text-align:center;box-shadow:0 2px 10px rgba(15,23,42,.06);position:relative;animation:fadeUp .4s ease both}
.rank img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:12px}
.rank .md{position:absolute;top:4px;left:8px;font-size:1.7rem;filter:drop-shadow(0 2px 3px rgba(0,0,0,.3))}
.rank .nm{font-weight:700;font-size:.84rem;color:#111827;margin-top:6px;line-height:1.2}
.rank .sv{color:#15803d;font-weight:800;font-size:.9rem}
/* ---------- Komponen bawaan ---------- */
[data-testid="stMetric"]{background:#fff;border-radius:16px;padding:14px 16px;border:1px solid #eef2f7;border-left:5px solid #16a34a;box-shadow:0 2px 10px rgba(15,23,42,.06);transition:.18s}
[data-testid="stMetric"]:hover{transform:translateY(-2px);box-shadow:0 10px 22px -12px rgba(15,23,42,.35)}
[data-testid="stMetricLabel"]{color:#64748b}
[data-testid="stMetricValue"]{font-weight:800;color:#0f172a}
div[data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"],div[data-testid="column"]:nth-child(2) [data-testid="stMetric"]{border-left-color:#f59e0b}
div[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"],div[data-testid="column"]:nth-child(3) [data-testid="stMetric"]{border-left-color:#0ea5e9}
div[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"],div[data-testid="column"]:nth-child(4) [data-testid="stMetric"]{border-left-color:#a855f7}
div[data-testid="stColumn"]:nth-child(5) [data-testid="stMetric"],div[data-testid="column"]:nth-child(5) [data-testid="stMetric"]{border-left-color:#ef4444}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#e8eef5;padding:5px;border-radius:14px}
.stTabs [data-baseweb="tab"]{border-radius:10px;padding:8px 16px;font-weight:600;height:auto}
.stTabs [aria-selected="true"]{background:#fff;color:#15803d;box-shadow:0 2px 8px rgba(0,0,0,.1)}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:12px;font-weight:600;transition:.15s;border:1px solid #d1d5db}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-1px);box-shadow:0 8px 16px -8px rgba(22,163,74,.55);border-color:#16a34a;color:#15803d}
button[kind="primary"],button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"]{background:linear-gradient(135deg,#22c55e,#15803d);color:#fff;border:0}
button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover,button[data-testid="stBaseButton-primaryFormSubmit"]:hover{color:#fff;filter:brightness(1.07)}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{border-radius:12px!important}
[data-testid="stDataFrame"]{border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(15,23,42,.07)}
[data-testid="stAlert"]{border-radius:14px}
[data-testid="stExpander"]{border-radius:14px;background:#fff}
/* ---------- Login ---------- */
.st-key-loginbox{background:#fff;border-radius:26px;padding:26px 30px;border:1px solid #dcfce7;box-shadow:0 26px 60px -26px rgba(22,163,74,.6);animation:fadeUp .5s ease both}
.login-hero{text-align:center;margin-bottom:6px}
.login-hero .logo{font-size:3.6rem;animation:float 3s ease-in-out infinite}
.login-hero .brand{font-weight:800;font-size:1.7rem;color:#14532d}
.login-hero .tag{color:#64748b;font-size:.88rem}
.login-hero .er{font-size:1.5rem;letter-spacing:6px;margin-top:8px}
.cihead img,.rank img{background:#fff}
"""
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)

# ───────────────────────── Util ─────────────────────────
def rp(n): return "Rp " + f"{int(round(n or 0)):,}".replace(",", ".")
def now(): return dt.datetime.now(TZ).replace(tzinfo=None).isoformat(" ", "seconds")
def today(): return dt.datetime.now(TZ).date()

def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"

def check_pw(pw, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_pw(pw, salt), stored)

def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")    # tahan mati lampu
    c.execute("PRAGMA synchronous=FULL")    # data langsung ditulis ke disk
    return c

def run(sql, p=()):
    with closing(conn()) as c:
        cur = c.execute(sql, p); c.commit(); return cur.lastrowid

def one(sql, p=()):
    with closing(conn()) as c:
        return c.execute(sql, p).fetchone()

def qdf(sql, p=()):
    with closing(conn()) as c:
        return pd.read_sql_query(sql, c, params=p)

def setting(k, d=""):
    r = one("SELECT v FROM settings WHERE k=?", (k,))
    return r["v"] if r else d

# ───────────────────────── Database ─────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, nama TEXT, role TEXT, pw TEXT);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, kode TEXT UNIQUE, nama TEXT, kategori TEXT, emoji TEXT, gambar TEXT,
  satuan TEXT, harga_beli REAL, harga_eceran REAL, harga_grosir REAL, min_grosir INTEGER, stok INTEGER, stok_min INTEGER, aktif INTEGER DEFAULT 1,
  gambar_url TEXT DEFAULT '', kata_cari TEXT DEFAULT '', sumber TEXT DEFAULT 'f', foto_coba INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS stock_moves(id INTEGER PRIMARY KEY, waktu TEXT, product_id INTEGER, tipe TEXT, qty INTEGER, stok_akhir INTEGER, ket TEXT, user TEXT);
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, nota TEXT UNIQUE, waktu TEXT, kasir TEXT, total REAL, modal REAL, untung REAL,
  metode TEXT, bayar REAL, kembali REAL, status TEXT DEFAULT 'OK');
CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER, product_id INTEGER, nama TEXT, kategori TEXT, qty INTEGER,
  harga REAL, mode TEXT, subtotal REAL, modal REAL);
CREATE TABLE IF NOT EXISTS cash(id INTEGER PRIMARY KEY, waktu TEXT, tipe TEXT, kategori TEXT, nominal REAL, ket TEXT, user TEXT, sale_id INTEGER);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS draft(username TEXT, product_id INTEGER, qty INTEGER, PRIMARY KEY(username, product_id));
"""

# Katalog kebutuhan harian rumah tangga.
# (nama, kategori, satuan, harga_beli, harga_eceran, harga_grosir, min_grosir, stok, stok_min, kata_cari, sumber)
#  kata_cari : kata kunci pencarian foto. Pisahkan alternatif dengan "|".
#              Bagian setelah "||" dipakai khusus untuk Wikimedia Commons (bahasa Inggris).
#  sumber    : f = kemasan makanan/minuman (Open Food Facts) · b = perawatan/kebersihan (Open Beauty/Products Facts)
#              w = barang umum (Wikimedia Commons) · x = tanpa foto (voucher)
# Stok sengaja dibuat bervariasi: rendah (<= batas kritis), sedang, dan tinggi, plus 2 barang habis.
SEED = [
 # ── Sembako: beras, telur, gula, minyak, tepung, garam, bawang ──
 ("Beras Premium 5 Kg","Sembako","sak",66000,72000,70000,4,30,8,"beras premium 5 kg|beras 5 kg||rice sack 5 kg","f"),
 ("Beras Premium 10 Kg","Sembako","sak",128000,138000,135000,3,22,6,"beras premium 10 kg|beras 10 kg||rice sack 10 kg","f"),
 ("Beras Premium 25 Kg (Sekarung)","Sembako","karung",315000,335000,328000,2,12,3,"beras 25 kg||rice sack 25 kg","f"),
 ("Beras Medium 5 Kg","Sembako","sak",58000,63000,61000,4,48,10,"beras 5 kg||rice sack 5 kg","f"),
 ("Beras Medium 10 Kg","Sembako","sak",112000,122000,119000,3,6,6,"beras 10 kg||rice sack","f"),
 ("Beras Medium 50 Kg (Sekarung Besar)","Sembako","karung",540000,575000,565000,2,3,3,"rice sack 50 kg","w"),
 ("Beras Merah 1 Kg","Sembako","kg",16000,19000,18000,5,24,6,"beras merah||brown rice","f"),
 ("Beras Ketan Putih 1 Kg","Sembako","kg",19000,22000,21000,5,18,5,"beras ketan putih||glutinous rice","f"),
 ("Beras Curah (Kiloan)","Sembako","kg",13000,15000,14000,10,52,20,"white rice grains","w"),
 ("Telur Ayam Ras (Butir)","Sembako","butir",2200,2600,2400,30,450,90,"chicken eggs","w"),
 ("Telur Ayam 1 Rak (30 Butir)","Sembako","rak",62000,70000,67000,3,28,6,"egg tray 30 eggs","w"),
 ("Telur Puyuh (Pack)","Sembako","pack",9000,11000,10000,6,14,5,"quail eggs","w"),
 ("Gula Pasir 1 Kg","Sembako","kg",16000,18000,17000,10,90,20,"gula pasir 1 kg||white sugar package","f"),
 ("Gula Pasir 50 Kg (Sekarung)","Sembako","karung",780000,820000,805000,2,3,3,"sugar sack 50 kg","w"),
 ("Gula Merah / Gula Aren 1 Kg","Sembako","kg",22000,26000,24000,5,12,4,"palm sugar gula aren","w"),
 ("Minyak Goreng Pouch 1 Liter","Sembako","pcs",16500,18500,17500,6,58,12,"minyak goreng 1 liter||cooking oil pouch","f"),
 ("Minyak Goreng Pouch 2 Liter","Sembako","pcs",32000,36000,34500,6,9,10,"minyak goreng 2 liter||cooking oil 2 liter","f"),
 ("Minyak Goreng 5 Liter (Jerigen)","Sembako","jerigen",78000,86000,83000,3,14,4,"minyak goreng 5 liter||cooking oil 5 liter","f"),
 ("Minyakita 1 Liter","Sembako","pcs",15700,17000,16500,6,50,12,"minyakita","f"),
 ("Minyak Goreng Curah 1 Liter","Sembako","liter",14000,16000,15000,6,26,10,"cooking oil bottle","w"),
 ("Tepung Terigu Segitiga Biru 1 Kg","Sembako","kg",11000,13500,12500,10,55,12,"tepung terigu segitiga biru","f"),
 ("Tepung Terigu Cakra Kembar 1 Kg","Sembako","kg",13000,15500,14500,10,8,10,"tepung terigu cakra kembar","f"),
 ("Tepung Terigu 25 Kg (Sekarung)","Sembako","karung",255000,275000,268000,2,12,2,"wheat flour sack 25 kg","w"),
 ("Tepung Beras Rose Brand 500 g","Sembako","pack",8000,10000,9000,6,16,8,"tepung beras rose brand","f"),
 ("Tepung Tapioka 500 g","Sembako","pack",7000,9000,8000,6,30,8,"tepung tapioka||tapioca flour","f"),
 ("Tepung Bumbu Serbaguna Sachet","Sembako","sachet",2200,3000,2700,20,150,30,"tepung bumbu serbaguna||seasoned flour","f"),
 ("Garam Dapur Halus 250 g","Sembako","pcs",2500,3500,3000,12,67,15,"garam beryodium 250 g||iodized salt","f"),
 ("Garam Beryodium 500 g","Sembako","pcs",4000,5000,4500,12,44,12,"garam beryodium 500 g||table salt","f"),
 ("Bawang Merah 1 Kg","Sembako","kg",38000,44000,41000,3,18,5,"shallots","w"),
 ("Bawang Putih 1 Kg","Sembako","kg",36000,42000,39000,3,4,5,"garlic bulbs","w"),
 ("Cabai Rawit Merah 250 g","Sembako","pack",18000,22000,20000,3,21,4,"bird's eye chili","w"),
 # ── Mie & makanan instan ──
 ("Indomie Mi Goreng Original","Mie & Instan","bungkus",2900,3500,3300,40,600,100,"indomie mi goreng","f"),
 ("Indomie Mi Goreng 1 Dus (40 Bks)","Mie & Instan","dus",112000,125000,120000,2,13,5,"indomie mi goreng","f"),
 ("Indomie Soto Mie","Mie & Instan","bungkus",2700,3300,3000,40,300,60,"indomie soto mie","f"),
 ("Indomie Ayam Bawang","Mie & Instan","bungkus",2700,3300,3000,40,80,60,"indomie ayam bawang","f"),
 ("Indomie Kari Ayam","Mie & Instan","bungkus",2800,3400,3100,40,45,60,"indomie kari ayam","f"),
 ("Indomie Goreng Rendang","Mie & Instan","bungkus",3000,3700,3400,40,35,40,"indomie rendang","f"),
 ("Mie Sedaap Goreng","Mie & Instan","bungkus",2800,3400,3100,40,226,50,"mie sedaap goreng","f"),
 ("Mie Sedaap Soto","Mie & Instan","bungkus",2600,3200,3000,40,150,50,"mie sedaap soto","f"),
 ("Supermi Ayam Bawang","Mie & Instan","bungkus",2600,3200,2900,40,90,40,"supermi ayam bawang","f"),
 ("Sarimi Ayam Bawang","Mie & Instan","bungkus",2500,3100,2900,40,0,40,"sarimi ayam bawang","f"),
 ("Pop Mie Ayam (Cup)","Mie & Instan","cup",5500,7000,6500,12,48,12,"pop mie ayam","f"),
 ("Mie Telur 3 Ayam 200 g","Mie & Instan","pack",4500,5500,5000,12,49,10,"mie telur 3 ayam","f"),
 ("Bihun Jagung 150 g","Mie & Instan","pack",4000,5000,4500,12,35,10,"bihun jagung||rice vermicelli","f"),
 ("Makaroni Kering 200 g","Mie & Instan","pack",5000,6500,6000,12,25,8,"makaroni||macaroni pasta","f"),
 ("Spaghetti La Fonte 450 g","Mie & Instan","pack",14000,17000,16000,6,20,4,"la fonte spaghetti","f"),
 ("Sarden ABC Kaleng 155 g","Mie & Instan","kaleng",9500,12000,11000,6,36,8,"sarden abc||sardines can","f"),
 ("Kornet Pronas 198 g","Mie & Instan","kaleng",17000,21000,19500,6,5,6,"kornet pronas||corned beef can","f"),
 # ── Bumbu dapur ──
 ("Kecap Manis ABC 275 ml","Bumbu Dapur","botol",11000,13500,12500,6,30,8,"kecap manis abc","f"),
 ("Kecap Manis Bango 220 ml (Pouch)","Bumbu Dapur","pouch",9000,11000,10000,6,26,10,"kecap manis bango","f"),
 ("Kecap Manis Sachet","Bumbu Dapur","sachet",700,1000,850,20,180,40,"kecap manis sachet","f"),
 ("Saus Sambal ABC 335 ml","Bumbu Dapur","botol",10000,12500,11500,6,24,6,"saus sambal abc","f"),
 ("Saus Sambal Sachet","Bumbu Dapur","sachet",600,1000,800,20,150,40,"saus sambal sachet","f"),
 ("Royco Penyedap Ayam Sachet","Bumbu Dapur","sachet",700,1000,850,20,100,50,"royco ayam","f"),
 ("Masako Ayam Sachet","Bumbu Dapur","sachet",600,1000,800,20,250,50,"masako ayam","f"),
 ("Sasa Penyedap Rasa 100 g","Bumbu Dapur","pcs",3000,4000,3500,12,70,15,"sasa penyedap rasa","f"),
 ("Ajinomoto 250 g","Bumbu Dapur","pack",8500,10500,9800,6,28,8,"ajinomoto","f"),
 ("Bumbu Racik Nasi Goreng Sachet","Bumbu Dapur","sachet",1400,2000,1700,12,120,30,"bumbu racik nasi goreng","f"),
 ("Santan Kara 65 ml","Bumbu Dapur","pcs",3500,4500,4000,12,39,15,"santan kara","f"),
 ("Santan Kara 200 ml","Bumbu Dapur","pcs",8000,10000,9200,6,7,8,"santan kara 200 ml","f"),
 ("Cuka Dapur Dixi 150 ml","Bumbu Dapur","botol",3500,5000,4500,6,28,6,"cuka dixi","f"),
 ("Margarin Blue Band 200 g","Bumbu Dapur","cup",7000,9000,8200,6,36,10,"blue band margarin","f"),
 ("Merica Bubuk Sachet","Bumbu Dapur","sachet",1500,2500,2000,12,60,15,"ladaku merica bubuk||ground pepper","f"),
 # ── Minuman: air mineral, galon, teh, kopi, susu ──
 ("Aqua Botol 600 ml","Minuman","botol",2200,3000,2600,24,144,72,"aqua 600 ml","f"),
 ("Aqua Botol 600 ml 1 Dus (24 Btl)","Minuman","dus",46000,54000,51000,2,40,8,"aqua 600 ml","f"),
 ("Aqua Botol 1,5 Liter","Minuman","botol",4800,6000,5500,12,112,24,"aqua 1.5 l|aqua 1500 ml","f"),
 ("Aqua Gelas 220 ml 1 Dus (48 Gls)","Minuman","dus",33000,40000,37000,3,30,8,"aqua gelas 220 ml|aqua cup","f"),
 ("Air Galon Aqua 19 Liter (Isi)","Minuman","galon",18000,23000,21000,5,20,6,"aqua galon 19 l||water gallon 19 liter","f"),
 ("Air Galon Isi Ulang 19 Liter","Minuman","galon",12000,16000,14500,5,40,10,"water gallon dispenser","w"),
 ("Galon Kosong 19 Liter","Minuman","galon",38000,48000,45000,2,5,5,"empty water gallon bottle","w"),
 ("Le Minerale 600 ml","Minuman","botol",2100,3000,2600,24,218,48,"le minerale 600 ml","f"),
 ("Le Minerale 1,5 Liter","Minuman","botol",4500,5500,5000,12,60,18,"le minerale 1.5 l","f"),
 ("Teh Botol Sosro 450 ml","Minuman","botol",3800,5000,4500,12,72,18,"teh botol sosro","f"),
 ("Teh Pucuk Harum 350 ml","Minuman","botol",3000,4000,3600,12,48,24,"teh pucuk harum","f"),
 ("Teh Celup Sariwangi 25 Kantong","Minuman","kotak",6000,7500,7000,10,60,12,"sariwangi teh celup","f"),
 ("Kopi Kapal Api Special Mix Sachet","Minuman","sachet",1200,1700,1500,20,270,60,"kapal api special mix","f"),
 ("Kopi Kapal Api Bubuk 165 g","Minuman","pack",13000,16000,15000,6,24,6,"kapal api kopi bubuk","f"),
 ("Good Day Cappuccino Sachet","Minuman","sachet",1500,2000,1800,20,104,40,"good day cappuccino","f"),
 ("Energen Coklat Sachet","Minuman","sachet",1800,2500,2200,10,120,30,"energen coklat","f"),
 ("Milo Sachet 27 g","Minuman","sachet",2000,2800,2500,10,25,40,"milo sachet","f"),
 ("Marimas Minuman Serbuk Sachet","Minuman","sachet",700,1000,850,20,80,40,"marimas","f"),
 ("Nutrisari Jeruk Sachet","Minuman","sachet",1100,1600,1400,20,138,30,"nutrisari jeruk","f"),
 ("Sirup Marjan Boudoin 460 ml","Minuman","botol",14000,18000,16500,6,20,6,"marjan boudoin sirup","f"),
 ("Susu Kental Manis Frisian Flag 370 g","Minuman","kaleng",11000,13500,12500,6,36,8,"frisian flag susu kental manis","f"),
 ("Susu Kental Manis Indomilk Sachet","Minuman","sachet",1600,2200,2000,20,96,30,"indomilk susu kental manis","f"),
 ("Susu UHT Ultra Milk Coklat 200 ml","Minuman","kotak",4500,5500,5000,12,72,18,"ultra milk coklat 200 ml","f"),
 ("Coca-Cola 390 ml","Minuman","botol",3800,5000,4500,12,82,18,"coca-cola 390 ml|coca cola","f"),
 ("Pocari Sweat 350 ml","Minuman","botol",5500,7000,6500,12,40,12,"pocari sweat 350 ml","f"),
 # ── Susu & perlengkapan bayi ──
 ("Susu Formula SGM Eksplor 1+ 400 g","Susu & Bayi","kotak",54000,62000,59000,3,12,4,"sgm eksplor 1+","f"),
 ("Susu Dancow 3+ Madu 400 g","Susu & Bayi","kotak",52000,60000,57000,3,22,4,"dancow 3+","f"),
 ("Botol Susu Bayi 240 ml","Susu & Bayi","pcs",15000,22000,19000,6,20,6,"baby feeding bottle","w"),
 ("Botol Susu Bayi 120 ml","Susu & Bayi","pcs",12000,18000,16000,6,6,6,"baby bottle","w"),
 ("Dot Botol Susu Silikon","Susu & Bayi","pcs",6000,10000,8500,6,30,8,"baby bottle nipple silicone","w"),
 ("Popok Bayi Sweety Pants M","Susu & Bayi","pack",55000,65000,62000,3,20,4,"sweety pants","b"),
 ("Popok Bayi Sweety Pants L","Susu & Bayi","pack",58000,68000,65000,3,3,4,"sweety pants","b"),
 ("Tisu Basah Bayi 50 Lembar","Susu & Bayi","pack",9000,12000,11000,6,30,8,"baby wipes","b"),
 ("Bubur Bayi SUN 120 g","Susu & Bayi","pack",9000,12000,11000,6,18,6,"bubur bayi sun||baby cereal","f"),
 ("Minyak Telon Lang 60 ml","Susu & Bayi","botol",13000,17000,15500,6,27,6,"minyak telon lang","b"),
 # ── Makanan ringan ──
 ("Biskuit Roma Kelapa","Makanan Ringan","pack",8500,11000,10000,10,26,10,"roma kelapa biskuit","f"),
 ("Biskuit Marie Regal 250 g","Makanan Ringan","pack",8000,10500,9500,10,5,8,"marie regal biskuit","f"),
 ("Oreo Original 133 g","Makanan Ringan","pack",7000,9000,8200,10,36,10,"oreo original","f"),
 ("Wafer Tango Coklat","Makanan Ringan","pcs",1800,2500,2200,20,120,30,"tango wafer coklat","f"),
 ("Chitato Sapi Panggang 68 g","Makanan Ringan","pcs",9500,12000,11000,10,48,10,"chitato sapi panggang","f"),
 ("Chiki Twist Jagung Bakar","Makanan Ringan","pcs",1800,2500,2200,20,50,25,"chiki twist","f"),
 ("Kerupuk Udang Mentah 250 g","Makanan Ringan","pack",9000,12000,11000,6,20,6,"kerupuk udang||shrimp crackers","f"),
 ("Roti Tawar Sari Roti","Makanan Ringan","bungkus",15500,18000,17000,5,23,5,"sari roti tawar","f"),
 ("Permen Kopiko (27 pcs)","Makanan Ringan","bungkus",7500,10000,9000,6,40,10,"kopiko coffee candy","f"),
 ("Coklat SilverQueen 58 g","Makanan Ringan","pcs",12000,15000,14000,6,20,6,"silverqueen","f"),
 ("Kacang Garuda 100 g","Makanan Ringan","pcs",8500,11000,10000,6,18,6,"garuda kacang||peanut snack","f"),
 ("Wafer Nabati Richeese","Makanan Ringan","pcs",2000,2800,2500,20,116,25,"nabati richeese","f"),
 # ── Gas & energi ──
 ("Gas Elpiji 3 Kg (Isi Ulang)","Gas & Energi","tabung",20000,24000,22500,5,30,8,"LPG cylinder 3 kg","w"),
 ("Tabung Gas 3 Kg + Isi (Baru)","Gas & Energi","tabung",190000,215000,205000,2,3,3,"LPG cylinder 3 kg","w"),
 ("Gas Bright Gas 5,5 Kg","Gas & Energi","tabung",95000,110000,105000,2,10,3,"LPG cylinder 5.5 kg","w"),
 ("Gas Elpiji 12 Kg","Gas & Energi","tabung",185000,205000,198000,2,6,6,"LPG cylinder 12 kg","w"),
 ("Regulator Gas + Selang","Gas & Energi","set",35000,50000,45000,3,20,4,"LPG regulator hose","w"),
 ("Kompor Gas 1 Tungku","Gas & Energi","unit",85000,110000,100000,2,4,4,"portable gas stove","w"),
 ("Korek Api Gas","Gas & Energi","pcs",1800,3000,2500,20,80,25,"gas lighter","w"),
 ("Baterai ABC AA (Isi 2)","Gas & Energi","pack",5500,8000,7000,10,40,10,"abc baterai alkaline aa","b"),
 ("Baterai ABC AAA (Isi 2)","Gas & Energi","pack",5500,8000,7000,10,8,10,"abc baterai alkaline aaa","b"),
 ("Lilin Putih (Isi 6)","Gas & Energi","pack",4000,6000,5000,10,28,8,"white candles","w"),
 ("Lampu LED 9 Watt","Gas & Energi","pcs",22000,30000,27000,6,36,8,"LED light bulb","w"),
 ("Arang Kayu 1 Kg","Gas & Energi","kg",9000,12000,11000,5,20,6,"charcoal","w"),
 ("Stop Kontak 4 Lubang + Kabel","Gas & Energi","pcs",18000,28000,25000,3,12,4,"power strip extension cord","w"),
 # ── Perabot rumah tangga: gelas, piring, botol, dus, ember ──
 ("Gelas Kaca Bening","Perabot Rumah Tangga","pcs",4000,6000,5000,12,111,24,"drinking glass tumbler","w"),
 ("Gelas Kaca 1 Lusin (12 pcs)","Perabot Rumah Tangga","lusin",42000,55000,50000,2,8,3,"drinking glasses set","w"),
 ("Gelas Plastik 16 oz (Isi 50)","Perabot Rumah Tangga","pack",11000,15000,13500,6,40,10,"plastic cups disposable","w"),
 ("Cangkir Keramik Putih","Perabot Rumah Tangga","pcs",5000,8000,7000,12,20,10,"white ceramic coffee cup","w"),
 ("Piring Melamin 9 Inch","Perabot Rumah Tangga","pcs",7000,11000,9500,12,37,8,"melamine plate","w"),
 ("Mangkok Melamin","Perabot Rumah Tangga","pcs",6000,9000,8000,12,30,8,"melamine bowl","w"),
 ("Sendok Makan Stainless","Perabot Rumah Tangga","pcs",2000,3500,3000,12,80,20,"stainless steel spoon","w"),
 ("Garpu Stainless","Perabot Rumah Tangga","pcs",2000,3500,3000,12,6,20,"stainless steel fork","w"),
 ("Toples Plastik 2 Liter","Perabot Rumah Tangga","pcs",11000,16000,14500,6,22,6,"plastic food storage jar","w"),
 ("Kotak Makan 2 Sekat","Perabot Rumah Tangga","pcs",14000,22000,19000,6,31,6,"lunch box container","w"),
 ("Botol Minum Plastik 750 ml","Perabot Rumah Tangga","pcs",9000,15000,13000,6,4,6,"plastic water bottle reusable","w"),
 ("Botol Minum Anak + Tali","Perabot Rumah Tangga","pcs",13000,20000,17500,6,14,5,"kids water bottle","w"),
 ("Botol Spray Plastik 500 ml","Perabot Rumah Tangga","pcs",6000,10000,8500,6,25,8,"spray bottle","w"),
 ("Termos Air Panas 1 Liter","Perabot Rumah Tangga","pcs",38000,52000,48000,3,20,4,"vacuum flask thermos","w"),
 ("Dus / Kardus Pindahan Besar","Perabot Rumah Tangga","pcs",5000,8000,7000,10,48,15,"cardboard box","w"),
 ("Dus Makan Kertas (Isi 25)","Perabot Rumah Tangga","pack",12000,18000,16000,6,30,8,"paper takeaway food box","w"),
 ("Ember Plastik 12 Liter","Perabot Rumah Tangga","pcs",14000,22000,19000,3,18,4,"plastic bucket","w"),
 ("Gayung Plastik","Perabot Rumah Tangga","pcs",4000,7000,6000,6,30,8,"plastic water dipper","w"),
 ("Baskom Plastik 25 cm","Perabot Rumah Tangga","pcs",7000,12000,10000,6,18,6,"plastic basin","w"),
 ("Panci Aluminium 20 cm","Perabot Rumah Tangga","pcs",40000,60000,55000,3,17,3,"aluminium cooking pot","w"),
 ("Wajan Penggorengan 28 cm","Perabot Rumah Tangga","pcs",45000,65000,60000,3,5,3,"frying pan wok","w"),
 ("Pisau Dapur","Perabot Rumah Tangga","pcs",8000,14000,12000,6,25,8,"kitchen knife","w"),
 ("Talenan Plastik","Perabot Rumah Tangga","pcs",8000,14000,12000,6,23,5,"plastic cutting board","w"),
 ("Plastik Kresek Hitam (Pack)","Perabot Rumah Tangga","pack",5000,7000,6200,10,40,10,"plastic carrier bags","w"),
 # ── Kebersihan rumah & cucian ──
 ("Sunlight Cuci Piring 400 ml","Kebersihan","pouch",8000,10500,9500,6,21,8,"sunlight jeruk nipis","b"),
 ("Deterjen Rinso 770 g","Kebersihan","pack",17000,21000,19500,6,30,8,"rinso detergent","b"),
 ("Deterjen Rinso Sachet","Kebersihan","sachet",700,1000,850,20,200,50,"rinso sachet","b"),
 ("Pewangi Molto Sachet","Kebersihan","sachet",800,1500,1200,20,139,30,"molto pewangi","b"),
 ("Pembersih Lantai Wipol 780 ml","Kebersihan","botol",11000,14000,13000,6,24,6,"wipol karbol","b"),
 ("Pemutih Bayclin 500 ml","Kebersihan","botol",10000,13000,12000,6,8,8,"bayclin","b"),
 ("Sabun Cuci Batang","Kebersihan","pcs",2500,4000,3500,12,48,15,"laundry soap bar","w"),
 ("Baygon Aerosol 600 ml","Kebersihan","kaleng",38000,46000,43000,3,10,4,"baygon aerosol","b"),
 ("Obat Nyamuk Bakar Fumakilla","Kebersihan","dus",4500,6000,5400,12,40,10,"fumakilla obat nyamuk bakar||mosquito coil","b"),
 ("Tisu Toilet Paseo 4 Roll","Kebersihan","pack",14000,18000,16500,6,38,8,"paseo toilet tissue","b"),
 ("Tisu Wajah Paseo 250 Lembar","Kebersihan","pack",10000,14000,13000,6,30,8,"paseo facial tissue","b"),
 ("Spons Cuci Piring","Kebersihan","pcs",2000,3500,3000,12,39,15,"dish sponge","w"),
 ("Sapu Plastik","Kebersihan","pcs",14000,22000,19000,3,18,4,"broom","w"),
 ("Sikat WC","Kebersihan","pcs",7000,12000,10000,6,14,5,"toilet brush","w"),
 ("Kantong Sampah Hitam (Isi 10)","Kebersihan","pack",6000,9000,8000,10,40,10,"garbage bags","w"),
 # ── Perawatan diri ──
 ("Sabun Mandi Lifebuoy Batang 80 g","Perawatan Diri","pcs",2800,4000,3500,12,48,24,"lifebuoy sabun batang","b"),
 ("Sabun Mandi Lux Batang","Perawatan Diri","pcs",3200,4500,4000,12,60,15,"lux sabun mandi","b"),
 ("Sabun Cair Lifebuoy Refill 450 ml","Perawatan Diri","pouch",17000,21000,19500,6,25,5,"lifebuoy body wash","b"),
 ("Shampoo Sunsilk Sachet","Perawatan Diri","sachet",500,1000,800,20,192,60,"sunsilk shampoo sachet","b"),
 ("Shampoo Pantene 170 ml","Perawatan Diri","botol",17000,22000,20500,6,12,4,"pantene shampoo","b"),
 ("Pasta Gigi Pepsodent 75 g","Perawatan Diri","pcs",7500,10000,9200,6,48,12,"pepsodent pasta gigi","b"),
 ("Pasta Gigi Close Up 75 g","Perawatan Diri","pcs",8000,10500,9700,6,0,10,"close up pasta gigi","b"),
 ("Sikat Gigi Dewasa","Perawatan Diri","pcs",3500,5000,4500,12,55,12,"toothbrush","w"),
 ("Pembalut Charm Reguler","Perawatan Diri","pack",8000,10500,9700,6,36,8,"charm pembalut","b"),
 ("Minyak Kayu Putih Cap Lang 60 ml","Perawatan Diri","botol",13000,17000,15500,6,12,6,"minyak kayu putih cap lang","b"),
 # ── Voucher (tanpa foto produk) ──
 ("Voucher Pulsa 5.000","Voucher","pcs",5500,6500,0,0,100,10,"","x"),
 ("Voucher Pulsa 10.000","Voucher","pcs",10500,11500,0,0,100,10,"","x"),
 ("Voucher Pulsa 20.000","Voucher","pcs",20500,22000,0,0,100,10,"","x"),
 ("Token Listrik 20.000","Voucher","pcs",20500,22500,0,0,100,10,"","x"),
 ("Token Listrik 50.000","Voucher","pcs",50500,52500,0,0,100,10,"","x"),
]
KATALOG_VER = "v2-kebutuhan-harian"
KATEGORI = ["Sembako", "Mie & Instan", "Bumbu Dapur", "Minuman", "Susu & Bayi", "Makanan Ringan", "Gas & Energi",
            "Perabot Rumah Tangga", "Kebersihan", "Perawatan Diri", "Voucher"]

# 1 owner + 3 kasir. Ubah di sini kalau komposisinya beda (hanya dipakai saat database masih kosong).
SEED_USERS = [("owner", "Pemilik Bulo Jaya", "owner", "owner123"), ("kasir1", "Kasir 1", "kasir", "kasir123"),
              ("kasir2", "Kasir 2", "kasir", "kasir123"), ("kasir3", "Kasir 3", "kasir", "kasir123")]

def migrate_schema():
    """Tambah kolom baru (foto & kata kunci) pada database lama tanpa menghapus data."""
    with closing(conn()) as c:
        have = {r["name"] for r in c.execute("PRAGMA table_info(products)")}
        for col, ddl in (("gambar_url", "TEXT DEFAULT ''"), ("kata_cari", "TEXT DEFAULT ''"),
                         ("sumber", "TEXT DEFAULT 'f'"), ("foto_coba", "INTEGER DEFAULT 0"),
                         ("barcode", "TEXT DEFAULT ''")):
            if col not in have: c.execute(f"ALTER TABLE products ADD COLUMN {col} {ddl}")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_products_barcode ON products(barcode) WHERE barcode<>''")
        c.commit()

def install_katalog():
    """Ganti katalog lama dengan katalog kebutuhan harian (sekali saja).
    Barang lama dinonaktifkan, bukan dihapus, sehingga riwayat penjualan, kas & mutasi tetap utuh."""
    if setting("katalog") == KATALOG_VER: return
    if os.path.exists(DB) and one("SELECT 1 FROM products"):
        bak = f"{DB}.backup_sebelum_katalog_baru"
        if not os.path.exists(bak):
            try: shutil.copy2(DB, bak)
            except OSError: pass
    with closing(conn()) as c:
        c.execute("UPDATE products SET aktif=0, kode=kode||'#lama'||id WHERE aktif=1")
        for i, s in enumerate(SEED, 1):
            nama, kat, sat, hb, he, hg, mg, stok, smin, cari, src = s
            pid = c.execute("INSERT INTO products(kode,nama,kategori,emoji,gambar,satuan,harga_beli,harga_eceran,harga_grosir,min_grosir,stok,stok_min,"
                            "gambar_url,kata_cari,sumber,foto_coba) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                            (f"BJ{i:03d}", nama, kat, "", "", sat, hb, he, hg, mg, stok, smin, "", cari, src)).lastrowid
            c.execute("INSERT INTO stock_moves(waktu,product_id,tipe,qty,stok_akhir,ket,user) VALUES(?,?,?,?,?,?,?)",
                      (now(), pid, "AWAL", stok, stok, "Stok awal katalog kebutuhan harian", "sistem"))
        c.execute("INSERT OR REPLACE INTO settings VALUES('katalog',?)", (KATALOG_VER,))
        c.commit()

def init_db():
    with closing(conn()) as c:
        c.executescript(SCHEMA); c.commit()
    migrate_schema()
    if not one("SELECT 1 FROM users"):
        for un, nm, rl, pw in SEED_USERS:
            run("INSERT INTO users(username,nama,role,pw) VALUES(?,?,?,?)", (un, nm, rl, hash_pw(pw)))
    if not one("SELECT 1 FROM settings WHERE k='toko'"):
        for k, v in {"toko": "UMKM Bulo Jaya", "alamat": "Makassar, Sulawesi Selatan", "footer": "Terima kasih, selamat berbelanja kembali!"}.items():
            run("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, v))
    install_katalog()
    backfill_barcode()

# ───────────────────────── Logika bisnis ─────────────────────────
def get_product(pid): return one("SELECT * FROM products WHERE id=? AND aktif=1", (int(pid),))
def by_kode(kode): return one("SELECT * FROM products WHERE (kode=? OR barcode=? OR lower(nama)=lower(?)) AND aktif=1", (kode.strip(), kode.strip(), kode.strip()))

# ── Barcode EAN-13 (barang >= HARGA_BARCODE_MIN) ──
def ean13(pid):
    d = f"899{int(pid):09d}"
    t = sum(int(x) * (3 if i % 2 else 1) for i, x in enumerate(d))
    return d + str((10 - t % 10) % 10)

def ensure_barcode(pid):
    p = one("SELECT harga_eceran, barcode FROM products WHERE id=?", (int(pid),))
    if p and (p["harga_eceran"] or 0) >= HARGA_BARCODE_MIN and not p["barcode"]:
        run("UPDATE products SET barcode=? WHERE id=?", (ean13(pid), int(pid)))

def backfill_barcode():
    with closing(conn()) as c:
        for r in c.execute("SELECT id FROM products WHERE aktif=1 AND harga_eceran>=? AND COALESCE(barcode,'')=''", (HARGA_BARCODE_MIN,)).fetchall():
            c.execute("UPDATE products SET barcode=? WHERE id=?", (ean13(r["id"]), r["id"]))
        c.commit()

def barcode_png(code):
    from barcode import EAN13
    from barcode.writer import ImageWriter
    buf = io.BytesIO(); EAN13(code[:12], writer=ImageWriter()).write(buf)
    return buf.getvalue()

# ── Keranjang disimpan di database (aman kalau mati lampu / browser tertutup) ──
def load_cart(username):
    with closing(conn()) as c:
        return {int(r["product_id"]): int(r["qty"]) for r in c.execute("SELECT product_id,qty FROM draft WHERE username=?", (username,))}

def save_cart():
    u = st.session_state.get("user")
    if not u: return
    cart = {int(k): int(v) for k, v in st.session_state.get("cart", {}).items()}
    if st.session_state.get("cart_saved") == cart: return
    with closing(conn()) as c:
        c.execute("DELETE FROM draft WHERE username=?", (u["username"],))
        c.executemany("INSERT INTO draft(username,product_id,qty) VALUES(?,?,?)", [(u["username"], k, v) for k, v in cart.items()])
        c.commit()
    st.session_state.cart_saved = dict(cart)

def price_for(p, qty):
    """Harga bertingkat: grosir aktif bila qty >= batas grosir."""
    if (p["harga_grosir"] or 0) > 0 and (p["min_grosir"] or 0) > 0 and qty >= p["min_grosir"]:
        return p["harga_grosir"], "GROSIR"
    return p["harga_eceran"], "ECER"

def move_stock(c, pid, delta, tipe, ket, user):
    stok = c.execute("SELECT stok FROM products WHERE id=?", (pid,)).fetchone()["stok"] + delta
    if stok < 0: raise ValueError("Stok tidak boleh negatif")
    c.execute("UPDATE products SET stok=? WHERE id=?", (stok, pid))
    c.execute("INSERT INTO stock_moves(waktu,product_id,tipe,qty,stok_akhir,ket,user) VALUES(?,?,?,?,?,?,?)", (now(), pid, tipe, delta, stok, ket, user))

def add_cash(c, tipe, kategori, nominal, ket, user, sale_id=None):
    c.execute("INSERT INTO cash(waktu,tipe,kategori,nominal,ket,user,sale_id) VALUES(?,?,?,?,?,?,?)", (now(), tipe, kategori, nominal, ket, user, sale_id))

def checkout(cart, metode, bayar, kasir):
    with closing(conn()) as c:
        try:
            items, total, modal = [], 0, 0
            for pid, qty in cart.items():
                p = c.execute("SELECT * FROM products WHERE id=?", (int(pid),)).fetchone()
                if not p or p["stok"] < qty: raise ValueError(f"Stok Tidak Mencukupi: {p['nama'] if p else pid}")
                harga, mode = price_for(p, qty)
                items.append((p, qty, harga, mode, harga * qty, p["harga_beli"] * qty))
                total += harga * qty; modal += p["harga_beli"] * qty
            if metode == "Tunai" and bayar < total: raise ValueError("Uang diterima kurang")
            bayar = bayar if metode == "Tunai" else total
            n = c.execute("SELECT COUNT(*) n FROM sales WHERE date(waktu)=date(?)", (now(),)).fetchone()["n"] + 1
            nota = f"BJ{today():%Y%m%d}-{n:04d}"
            sid = c.execute("INSERT INTO sales(nota,waktu,kasir,total,modal,untung,metode,bayar,kembali) VALUES(?,?,?,?,?,?,?,?,?)",
                            (nota, now(), kasir, total, modal, total - modal, metode, bayar, bayar - total)).lastrowid
            for p, qty, harga, mode, sub, mdl in items:
                c.execute("INSERT INTO sale_items(sale_id,product_id,nama,kategori,qty,harga,mode,subtotal,modal) VALUES(?,?,?,?,?,?,?,?,?)",
                          (sid, p["id"], p["nama"], p["kategori"], qty, harga, mode, sub, mdl))
                move_stock(c, p["id"], -qty, "PENJUALAN", nota, kasir)
            add_cash(c, "MASUK", "Penjualan", total, nota, kasir, sid)
            c.commit()
        except Exception:
            c.rollback(); raise
    return sid

def void_sale(sid, user):
    with closing(conn()) as c:
        try:
            s = c.execute("SELECT * FROM sales WHERE id=?", (sid,)).fetchone()
            if s["status"] != "OK": raise ValueError("Transaksi sudah dibatalkan")
            for it in c.execute("SELECT * FROM sale_items WHERE sale_id=?", (sid,)).fetchall():
                move_stock(c, it["product_id"], it["qty"], "BATAL", f"Batal {s['nota']}", user)
            c.execute("UPDATE sales SET status='BATAL' WHERE id=?", (sid,))
            add_cash(c, "KELUAR", "Pembatalan Penjualan", s["total"], s["nota"], user, sid)
            c.commit()
        except Exception:
            c.rollback(); raise

def receipt_text(sid):
    s = one("SELECT * FROM sales WHERE id=?", (sid,))
    its = qdf("SELECT * FROM sale_items WHERE sale_id=?", (sid,))
    W = 34
    L = [setting("toko").center(W), setting("alamat").center(W), "=" * W, f"No   : {s['nota']}", f"Waktu: {s['waktu']}", f"Kasir: {s['kasir']}", "-" * W]
    for r in its.itertuples():
        L.append(r.nama[:W]); tag = " [GROSIR]" if r.mode == "GROSIR" else ""
        L.append(f"  {r.qty} x {int(r.harga):,}".replace(",", ".") + tag)
        L.append(f"{rp(r.subtotal):>{W}}")
    L += ["-" * W, f"{'TOTAL':<12}{rp(s['total']):>{W-12}}", f"{s['metode']:<12}{rp(s['bayar']):>{W-12}}", f"{'Kembali':<12}{rp(s['kembali']):>{W-12}}", "=" * W, setting("footer").center(W)]
    return "\n".join(L)

# ───────────────────────── Foto produk asli dari internet ─────────────────────────
# Sumber terbuka: Open Food Facts / Open Beauty Facts / Open Products Facts (foto kemasan, CC BY-SA)
# dan Wikimedia Commons (barang umum). Diunduh pelan-pelan di latar belakang & disimpan di folder gambar_produk,
# jadi hanya perlu internet sekali. Batas Open Food Facts: 10 pencarian/menit/IP, karena itu ada jeda antar permintaan.
UA = f"BuloJayaPOS/2.0 ({os.environ.get('POS_CONTACT', 'kasir@bulojaya.local')})"

@st.cache_resource
def _net():
    """Status bersama lintas rerun Streamlit (kunci, jeda antar permintaan, cache hasil pencarian)."""
    return {"tl": threading.Lock(), "sl": threading.Lock(), "last": {}, "urls": {}}
_N = _net()

class NetError(Exception):
    """Internet mati / server sibuk (bukan berarti fotonya tidak ada)."""

def _throttle(key, gap):
    with _N["tl"]:
        wait = _N["last"].get(key, 0) + gap - time.time()
        if wait > 0: time.sleep(wait)
        _N["last"][key] = time.time()

def http_get(url, timeout=15, limit=8_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(limit + 1)
    except urllib.error.HTTPError as e:
        if e.code in (429, 502, 503, 504): raise NetError(f"server sibuk (HTTP {e.code})") from e
        raise ValueError(f"HTTP {e.code}") from e
    except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
        raise NetError(str(e)) from e
    if len(data) > limit: raise ValueError("file terlalu besar")
    return data

def _jget(url): return json.loads(http_get(url).decode("utf-8", "replace"))

def _teks(v):
    if isinstance(v, str): return v
    if isinstance(v, (list, tuple)): return " ".join(_teks(x) for x in v)
    if isinstance(v, dict): return " ".join(_teks(x) for x in v.values())
    return ""

def _skor(q, teks):
    """Seberapa cocok teks dengan kata kunci. 0 = tidak cocok (kata utama/brand harus ada)."""
    toks = re.findall(r"[a-z0-9]+", q.lower())
    kata = [t for t in toks if not t.isdigit() and len(t) >= 3]
    if not kata: return 1
    tl = teks.lower()
    if kata[0] not in tl: return 0
    return sum(t in tl for t in toks if len(t) >= 2 or t.isdigit())

def _gambar_dari(h):
    for k in ("image_front_url", "image_url", "image_front_small_url", "image_small_url"):
        u = h.get(k)
        if isinstance(u, str) and u.startswith("http"): return u
    try:
        for u in (h.get("selected_images") or {}).get("front", {}).get("display", {}).values():
            if isinstance(u, str) and u.startswith("http"): return u
    except AttributeError: pass
    return None

def _off_produk(kode):
    """Ambil URL foto depan dari barcode (batas 15 permintaan/menit)."""
    _throttle("off_produk", 4.5)
    d = _jget(f"https://world.openfoodfacts.org/api/v2/product/{urllib.parse.quote(str(kode))}.json?fields=image_front_url,image_url")
    return _gambar_dari(d.get("product") or {})

def _pilih(q, hits, teks_fn, resolve):
    ranked = sorted(((_skor(q, teks_fn(h)), -i, h) for i, h in enumerate(hits)), key=lambda x: (x[0], x[1]), reverse=True)
    for sk, _, h in ranked[:3]:
        if sk <= 0: break
        try: u = resolve(h)
        except ValueError: u = None
        if u: return u
    return None

def off_sal(q):
    """Open Food Facts via Search-a-licious (pencarian teks resmi). Utamakan produk yang dijual di Indonesia."""
    def cari(query):
        _throttle("sal", 1.5)
        return _jget("https://search.openfoodfacts.org/search?" + urllib.parse.urlencode({"q": query, "page_size": 10})).get("hits") or []
    def resolve(h):
        return _gambar_dari(h) or (_off_produk(h["code"]) if h.get("code") else None)
    teks = lambda h: _teks([h.get("product_name"), h.get("brands"), h.get("generic_name")])
    for query in (f'{q} countries_tags:"en:indonesia"', q):
        try: hits = cari(query)
        except ValueError: continue          # sintaks filter ditolak server → coba tanpa filter
        u = _pilih(q, hits, teks, resolve)
        if u: return u
    return None

def legacy_cari(host, q):
    """Open Beauty Facts / Open Products Facts (API pencarian lama)."""
    _throttle(host, 6.5)
    d = _jget(f"https://{host}/cgi/search.pl?" + urllib.parse.urlencode(
        {"search_terms": q, "search_simple": 1, "action": "process", "json": 1, "page_size": 10}))
    return _pilih(q, d.get("products") or [], lambda h: _teks([h.get("product_name"), h.get("brands"), h.get("generic_name")]), _gambar_dari)

def commons_cari(q):
    """Wikimedia Commons — foto barang umum (galon, gelas, tabung gas, dsb.)."""
    _throttle("commons", 1.0)
    d = _jget("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": q + " filetype:bitmap", "gsrnamespace": 6,
        "gsrlimit": 10, "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": 700}))
    pages = sorted(((d.get("query") or {}).get("pages") or {}).values(), key=lambda x: x.get("index", 99))
    cands = []
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"): continue
        if min(ii.get("width", 0), ii.get("height", 0)) < 250: continue
        u = ii.get("thumburl") or ii.get("url")
        if u: cands.append((_skor(q, pg.get("title", "")), u))
    if not cands: return None
    best = max(cands, key=lambda x: x[0])          # urutan relevansi Commons dipakai bila skor sama
    return best[1] if best[0] > 0 else cands[0][1]

def cari_url_foto(p):
    """Tentukan URL foto untuk satu barang (baris produk). None = tidak ketemu. NetError = masalah jaringan."""
    if (p["gambar_url"] or "").strip(): return p["gambar_url"].strip()
    src = p["sumber"] or "f"
    if src == "x": return None
    db_part, _, w_part = (p["kata_cari"] or p["nama"]).partition("||")
    q_db = [q.strip() for q in db_part.split("|") if q.strip()][:2]
    q_w = [q.strip() for q in (w_part or db_part).split("|") if q.strip()][:2]
    plan = []
    if src == "f": plan += [("sal", q) for q in q_db]
    if src == "b" and q_db: plan += [("obf", q_db[0]), ("opf", q_db[0])]
    plan += [("wiki", q) for q in q_w]
    fn = {"sal": off_sal, "obf": lambda q: legacy_cari("world.openbeautyfacts.org", q),
          "opf": lambda q: legacy_cari("world.openproductsfacts.org", q), "wiki": commons_cari}
    net = False
    for kind, q in plan:
        key = (kind, q.lower())
        if key not in _N["urls"]:
            try: _N["urls"][key] = fn[kind](q)
            except NetError: net = True; continue
            except (ValueError, KeyError, TypeError, AttributeError): _N["urls"][key] = None
        if _N["urls"][key]: return _N["urls"][key]
    if net: raise NetError("jaringan bermasalah")
    return None

def simpan_foto(tag, data):
    """Validasi & simpan foto sebagai JPEG (latar transparan → putih). Mengembalikan path file."""
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(data)); im.load()
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel("A")); im = bg
    else: im = im.convert("RGB")
    if min(im.size) < 100: raise ValueError("gambar terlalu kecil")
    im.thumbnail((900, 900))
    path = os.path.join(IMG_DIR, f"{tag}_{secrets.token_hex(3)}.jpg")
    im.save(path, "JPEG", quality=88)
    return path

def ambil_foto(pid):
    """Cari & unduh foto satu barang. Return (ok, pesan). NetError bila internet bermasalah."""
    p = one("SELECT * FROM products WHERE id=?", (int(pid),))
    if not p: return False, "Barang tidak ditemukan"
    try:
        url = cari_url_foto(p)
        if not url: raise LookupError("foto belum ketemu di sumber terbuka")
        path = simpan_foto(f"p{pid}", http_get(url))
    except NetError: raise
    except Exception as e:
        run("UPDATE products SET foto_coba=foto_coba+1 WHERE id=?", (int(pid),))
        return False, str(e) or e.__class__.__name__
    run("UPDATE products SET gambar=?, foto_coba=0 WHERE id=?", (path, int(pid)))
    return True, "OK"

@st.cache_resource
def photo_state(): return {"running": False, "offline": False, "last": ""}

def _foto_loop(S):
    gagal_net = 0
    try:
        while True:
            r = one("SELECT id,nama FROM products WHERE aktif=1 AND COALESCE(sumber,'f')<>'x' AND COALESCE(gambar,'')='' AND COALESCE(foto_coba,0)=0 ORDER BY id LIMIT 1")
            if not r: break
            S["last"] = r["nama"]
            try: ambil_foto(r["id"]); gagal_net = 0
            except NetError:
                gagal_net += 1
                if gagal_net >= 3: S["offline"] = True; break
                time.sleep(5)
    except Exception: pass
    finally: S["running"] = False

def mulai_unduh_foto(ulang=False):
    """Mulai pekerja latar belakang (aman dipanggil berulang)."""
    S = photo_state()
    if ulang:
        run("UPDATE products SET foto_coba=0 WHERE aktif=1 AND COALESCE(gambar,'')=''"); _N["urls"].clear(); S["offline"] = False
    with _N["sl"]:
        if S["running"] or S["offline"]: return
        if not one("SELECT 1 FROM products WHERE aktif=1 AND COALESCE(sumber,'f')<>'x' AND COALESCE(gambar,'')='' AND COALESCE(foto_coba,0)=0 LIMIT 1"): return
        S["running"] = True
    threading.Thread(target=_foto_loop, args=(S,), daemon=True, name="foto-worker").start()

def foto_stats():
    r = one("SELECT COUNT(*) n, SUM(CASE WHEN COALESCE(gambar,'')<>'' THEN 1 ELSE 0 END) ada, "
            "SUM(CASE WHEN COALESCE(gambar,'')='' AND COALESCE(foto_coba,0)>0 THEN 1 ELSE 0 END) gagal "
            "FROM products WHERE aktif=1 AND COALESCE(sumber,'f')<>'x'")
    return int(r["n"] or 0), int(r["ada"] or 0), int(r["gagal"] or 0)

def _foto_body(compact):
    S = photo_state(); n, ada, gagal = foto_stats()
    if not n: return
    if S["running"] and compact:
        st.caption(f"📸 Mengunduh foto asli produk di latar belakang… {ada}/{n} siap — aplikasi tetap bisa dipakai.")
    elif S["running"]:
        st.info(f"📸 Mengunduh foto asli produk dari internet… **{ada}/{n}** siap (sekarang: {S['last']}). "
                "Berjalan di latar belakang — aplikasi tetap bisa dipakai. Barang tanpa foto sementara memakai gambar nama.")
    elif S["offline"]:
        st.warning("📡 Tidak bisa terhubung ke server foto (internet mati / server sibuk). Barang tanpa foto sementara memakai gambar nama.")
        if st.button("📥 Coba unduh lagi", key=f"foto_retry_{int(compact)}"): mulai_unduh_foto(ulang=True); st.rerun()
    elif gagal and not compact:
        st.caption(f"📷 {ada}/{n} barang sudah berfoto asli. {gagal} barang belum ketemu fotonya otomatis — "
                   "unggah foto / tempel URL foto di tab **Kelola Barang**, atau coba cari ulang.")
        if st.button("🔎 Cari ulang foto yang belum ada", key="foto_retry_0"): mulai_unduh_foto(ulang=True); st.rerun()
    baru = ada - st.session_state.get("foto_rendered", ada)
    if baru > 0 and st.button(f"🔄 {baru} foto baru siap — klik untuk menampilkan", key=f"foto_new_{int(compact)}", type="primary"): st.rerun()

def foto_status(compact=False):
    """Status unduhan foto; memperbarui diri tiap 5 detik selama unduhan berjalan."""
    S = photo_state()
    st.session_state.foto_rendered = foto_stats()[1]
    st.fragment(run_every=5 if S["running"] else None)(_foto_body)(compact)

# ───────────────────────── Tampilan: gambar produk & kartu ─────────────────────────
esc = html.escape
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
CAT_ICON = {"Semua": "🏪", "Sembako": "🌾", "Mie & Instan": "🍜", "Bumbu Dapur": "🧂", "Minuman": "🥤", "Susu & Bayi": "🍼",
            "Makanan Ringan": "🍪", "Gas & Energi": "🔥", "Perabot Rumah Tangga": "🍽️", "Kebersihan": "🧹", "Perawatan Diri": "🧴",
            "Voucher": "🎟️", "Makanan": "🍜", "Kebutuhan": "🧼"}
CAT_PAL = {  # (warna terang, warna tengah, warna teks)
    "Sembako": ("#fde68a", "#f59e0b", "#92400e"), "Mie & Instan": ("#fed7aa", "#fb923c", "#9a3412"),
    "Bumbu Dapur": ("#fecaca", "#f87171", "#991b1b"), "Minuman": ("#bae6fd", "#38bdf8", "#075985"),
    "Susu & Bayi": ("#fbcfe8", "#f472b6", "#9d174d"), "Makanan Ringan": ("#fef08a", "#facc15", "#854d0e"),
    "Gas & Energi": ("#fecdd3", "#fb7185", "#9f1239"), "Perabot Rumah Tangga": ("#a7f3d0", "#34d399", "#065f46"),
    "Kebersihan": ("#ddd6fe", "#a78bfa", "#5b21b6"), "Perawatan Diri": ("#bfdbfe", "#60a5fa", "#1e40af"),
    "Voucher": ("#c7d2fe", "#818cf8", "#3730a3"), "Makanan": ("#fecaca", "#fb7185", "#9f1239"), "Kebutuhan": ("#ddd6fe", "#a78bfa", "#5b21b6"),
}

def daftar_kategori():
    ada = qdf("SELECT DISTINCT kategori FROM products WHERE aktif=1")["kategori"].tolist()
    return [k for k in KATEGORI if k in ada] + sorted(k for k in ada if k not in KATEGORI)

@st.cache_data(show_spinner=False)
def product_art(nama, kategori, emoji, satuan):
    """Gambar sementara (tanpa emoji) bila foto asli belum ada: kartu nama barang di atas warna kategori."""
    a, b, c = CAT_PAL.get(kategori, ("#bbf7d0", "#4ade80", "#166534"))
    n = int(hashlib.md5(nama.encode()).hexdigest()[:8], 16)
    ang, c1x, c2x = 20 + n % 60, 30 + n % 110, 330 + (n >> 3) % 120
    wr = textwrap.wrap(nama, 17) or [nama[:17]]
    lines = wr[:3]
    if len(wr) > 3: lines[-1] = lines[-1][:15] + "…"
    h = 20 + 40 * len(lines) + 44
    y0 = (360 - h) // 2 - 6
    txt = "".join(f'<text x="240" y="{y0 + 50 + i * 40}" font-size="30" font-weight="700" fill="{c}" text-anchor="middle" '
                  f'font-family="Arial,sans-serif">{esc(l)}</text>' for i, l in enumerate(lines))
    lab = esc(f"foto belum tersedia · per {satuan}" if satuan else "foto belum tersedia")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360">'
           f'<defs><linearGradient id="g" gradientTransform="rotate({ang} .5 .5)"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>'
           f'<rect width="480" height="360" fill="url(#g)"/>'
           f'<circle cx="{c1x}" cy="40" r="70" fill="#fff" opacity=".2"/><circle cx="{c2x}" cy="320" r="90" fill="#fff" opacity=".16"/>'
           f'<rect x="40" y="{y0}" width="400" height="{h}" rx="26" fill="#fff" opacity=".94"/>{txt}'
           f'<text x="240" y="{y0 + h - 16}" font-size="15" fill="#94a3b8" text-anchor="middle" font-family="Arial,sans-serif">{lab}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

@st.cache_data(show_spinner=False)
def photo_uri(path, mtime, size=(360, 270), q=76):
    """Foto asli → dimuat utuh di atas latar putih (kemasan tidak terpotong) & dikecilkan supaya halaman tetap ringan."""
    try:
        from PIL import Image, ImageOps
        im = ImageOps.pad(ImageOps.exif_transpose(Image.open(path)).convert("RGB"), size, color=(255, 255, 255))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=q)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""

def prod_img(nama, kategori, emoji, satuan, gambar):
    if isinstance(gambar, str) and gambar and os.path.exists(gambar):
        u = photo_uri(gambar, os.path.getmtime(gambar))
        if u: return u
    return product_art(str(nama), str(kategori or ""), "", str(satuan or ""))

def thumb_uri(gambar):
    """Thumbnail kecil untuk tabel; None bila belum ada foto."""
    if isinstance(gambar, str) and gambar and os.path.exists(gambar):
        return photo_uri(gambar, os.path.getmtime(gambar), (96, 72), 70) or None
    return None

def stock_pct(stok, smin): return 0 if stok <= 0 else max(8, min(100, round(stok / (max(smin, 1) * 4) * 100)))

def card_html(r, incart=0):
    """Kartu produk (gambar + harga + bar stok). r = baris dari df.itertuples()."""
    stok, smin = int(r.stok), int(r.stok_min or 0)
    src = prod_img(r.nama, r.kategori, r.emoji, r.satuan, r.gambar)
    if stok <= 0: tl, col, out = "<span class='tg tl out'>HABIS</span>", "#ef4444", "out"
    elif stok <= smin: tl, col, out = "<span class='tg tl low'>⚠ MENIPIS</span>", "#f59e0b", ""
    else: tl, col, out = "", "#16a34a", ""
    tr = f"<span class='tg tr cart'>🛒 {incart}</span>" if incart else ""
    hg = r.harga_grosir if pd.notna(r.harga_grosir) else 0
    mg = r.min_grosir if pd.notna(r.min_grosir) else 0
    gr = f"<div class='gr'>Grosir {rp(hg)} · min {int(mg)}</div>" if hg > 0 and mg > 0 else "<div class='gr none'>&nbsp;</div>"
    return (f"<div class='pimg {out}'><img src='{src}' alt=''>{tl}{tr}<span class='tg bl kat'>{esc(str(r.kategori))}</span></div>"
            f"<div class='pbody'><div class='nm'>{esc(str(r.nama))}</div><div class='pr'>{rp(r.harga_eceran)}</div>{gr}"
            f"<div class='sbar'><i style='width:{stock_pct(stok, smin)}%;background:{col}'></i></div>"
            f"<div class='sinfo'><span>Stok</span><b style='color:{col}'>{stok} {esc(str(r.satuan or ''))}</b></div></div>")

def page_head(icon, title, sub=""):
    st.markdown(f"<div class='phead'><div class='ic'>{icon}</div><div><div class='tt'>{esc(title)}</div><div class='ss'>{esc(sub)}</div></div></div>", unsafe_allow_html=True)

def sapaan():
    h = dt.datetime.now(TZ).hour
    return ("Selamat pagi", "☀️") if h < 11 else ("Selamat siang", "🌤️") if h < 15 else ("Selamat sore", "🌇") if h < 18 else ("Selamat malam", "🌙")

def hero_kasir(u):
    t = today()
    s = one("SELECT COUNT(*) n, COALESCE(SUM(total),0) t FROM sales WHERE status='OK' AND date(waktu)=?", (str(t),))
    low = one("SELECT COUNT(*) n FROM products WHERE aktif=1 AND stok<=stok_min")["n"]
    chips = [f"📅 {HARI[t.weekday()]}, {t.day} {BULAN[t.month - 1]} {t.year}", f"🧾 {s['n']} transaksi hari ini"]
    if u["role"] == "owner": chips.append(f"💰 Omset {rp(s['t'])}")
    chips.append(f"🛒 {sum(st.session_state.cart.values())} item di keranjang")
    if low: chips.append(f"⚠️ {low} barang stok menipis")
    hi, ic = sapaan()
    st.markdown(f"<div class='hero'><div class='wv'>{ic}</div><div class='t'>{hi}, {esc(u['nama'])}! 👋</div>"
                f"<div class='s'>Siap melayani pelanggan — semoga laris manis hari ini 🍀</div>"
                f"<div class='chips'>{''.join(f'<span class=chip>{esc(c)}</span>' for c in chips)}</div></div>", unsafe_allow_html=True)

def promo_ticker():
    d = qdf("SELECT nama,satuan,harga_eceran,harga_grosir,min_grosir FROM products WHERE aktif=1 AND stok>0 AND harga_grosir>0 AND min_grosir>0 "
            "ORDER BY (harga_eceran-harga_grosir)*1.0/harga_eceran DESC LIMIT 8")
    if d.empty: return
    tx = "  ✦  ".join(f"🔥 {r.nama}: beli ≥{int(r.min_grosir)} {r.satuan} jadi {rp(r.harga_grosir)}/{r.satuan} (hemat {rp(r.harga_eceran - r.harga_grosir)})" for r in d.itertuples())
    st.markdown(f"<div class='ticker'><div class='in'>{esc(tx)}</div></div>", unsafe_allow_html=True)

# ───────────────────────── Scan: barcode & AI ─────────────────────────
def _strs(x):
    if isinstance(x, str): return [x] if x else []
    if isinstance(x, (list, tuple)): return [s for i in x for s in _strs(i)]
    return []

def decode_barcodes(data):
    out = []
    try:
        import numpy as np, cv2
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        try:
            det = cv2.barcode.BarcodeDetector()
            if hasattr(det, "detectAndDecodeWithType"): out += _strs(det.detectAndDecodeWithType(img)[1])
            else: out += _strs(det.detectAndDecode(img)[1])
        except Exception: pass
        try: out += _strs(cv2.QRCodeDetector().detectAndDecode(img)[0])
        except Exception: pass
    except ImportError:
        st.warning("Library opencv belum terpasang: pip install opencv-python-headless")
    return out

def ai_identify(data, mime):
    """Kenali produk dari foto memakai Claude Vision (opsional, butuh ANTHROPIC_API_KEY)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: return None, "Isi dulu variabel lingkungan ANTHROPIC_API_KEY untuk memakai fitur AI."
    try:
        import anthropic
        cat = qdf("SELECT id,nama FROM products WHERE aktif=1")
        daftar = "\n".join(f"{r.id}|{r.nama}" for r in cat.itertuples())
        msg = anthropic.Anthropic(api_key=key).messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), max_tokens=100,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime or "image/jpeg", "data": base64.b64encode(data).decode()}},
                {"type": "text", "text": f"Foto ini adalah barang di toko sembako. Pilih barang yang paling cocok dari daftar (format id|nama):\n{daftar}\n\n"
                                         'Balas HANYA JSON: {"id": <angka atau null>, "alasan": "<singkat>"}'}]}])
        m = re.search(r"\{.*\}", msg.content[0].text, re.S)
        j = json.loads(m.group(0)) if m else {}
        return j.get("id"), j.get("alasan", "")
    except Exception as e:
        return None, f"AI gagal: {e}"

# ───────────────────────── Keranjang ─────────────────────────
def flash(kind, msg): st.session_state.flash = (kind, msg)

def cart_add(pid, n=1):
    cart, k = st.session_state.cart, f"q_{pid}"
    cur = int(st.session_state.get(k, cart.get(pid, 0)))
    st.session_state[k] = cur + n; cart[pid] = cur + n

def cart_step(pid, d):
    k = f"q_{pid}"; v = int(st.session_state.get(k, 1)) + d
    if v < 1: cart_del(pid)
    else: st.session_state[k] = v; st.session_state.cart[pid] = v

def cart_del(pid):
    st.session_state.cart.pop(pid, None); st.session_state.pop(f"q_{pid}", None)

def cart_clear():
    for pid in list(st.session_state.cart): cart_del(pid)

def add_by_code(kode):
    p = by_kode(kode)
    if not p: flash("error", f"Kode '{kode}' tidak ditemukan"); return False
    if p["stok"] <= 0: flash("error", f"{p['nama']} stok habis"); return False
    cart_add(int(p["id"])); flash("success", f"✔ {p['nama']} ditambahkan"); return True

def scan_manual():
    v = st.session_state.get("kode_in", "").strip()
    if v: add_by_code(v)
    st.session_state.kode_in = ""

# ───────────────────────── Halaman: Kasir ─────────────────────────
def scan_tab():
    st.text_input("⌨️ Ketik / scan kode barang (scanner USB) lalu Enter", key="kode_in", on_change=scan_manual, placeholder="contoh: BJ001 atau arahkan scanner ke barcode")
    mode = st.radio("Kamera", ["Mati", "Scan Barcode", "Kenali dengan AI"], horizontal=True)
    if mode == "Mati": return
    img = st.camera_input("Arahkan barcode / foto barang", key=f"cam_{mode}")
    if not img: return
    data = img.getvalue(); h = hashlib.md5(data).hexdigest()
    if st.session_state.get("last_img") == h: return
    st.session_state.last_img = h
    if mode == "Scan Barcode":
        codes = decode_barcodes(data)
        if not codes: flash("warning", "Barcode tidak terbaca, coba lebih dekat / ketik manual.")
        else:
            for cd in dict.fromkeys(codes):
                if add_by_code(cd): break
    else:
        with st.spinner("AI mengenali barang..."):
            pid, ket = ai_identify(data, img.type)
        p = get_product(pid) if pid else None
        if p and p["stok"] > 0: cart_add(int(p["id"])); flash("success", f"🤖 AI mengenali: {p['nama']} — {ket}")
        else: flash("warning", f"AI tidak yakin. {ket or ''}")
    st.rerun()

SORTS = {
    "Nama A–Z": "p.nama", "🔥 Terlaris": "COALESCE(t.q,0) DESC, p.nama", "Harga termurah": "p.harga_eceran, p.nama",
    "Harga termahal": "p.harga_eceran DESC, p.nama", "Stok terbanyak": "p.stok DESC, p.nama", "⚠️ Stok menipis dulu": "(p.stok<=p.stok_min) DESC, p.stok, p.nama",
}

def catalog_tab():
    c1, c2 = st.columns([2, 1])
    s = c1.text_input("🔎 Cari barang", key="cat_s", placeholder="ketik nama barang, mis. beras, indomie, aqua, gas…")
    srt = c2.selectbox("Urutkan", list(SORTS), key="cat_o")
    cats = ["Semua"] + daftar_kategori()
    k = st.radio("Kategori", cats, horizontal=True, key="cat_k", label_visibility="collapsed", format_func=lambda c: f"{CAT_ICON.get(c, '📦')} {c}")
    sig = (s, srt, k)
    if st.session_state.get("cat_sig") != sig: st.session_state.cat_sig = sig; st.session_state.cat_lim = 45
    lim = st.session_state.get("cat_lim", 45)
    where, p = " WHERE p.aktif=1", []
    if k != "Semua": where += " AND p.kategori=?"; p.append(k)
    if s: where += " AND p.nama LIKE ?"; p.append(f"%{s}%")
    total = int(one("SELECT COUNT(*) n FROM products p" + where, p)["n"])
    df = qdf("SELECT p.* FROM products p LEFT JOIN (SELECT i.product_id pid, SUM(i.qty) q FROM sale_items i JOIN sales s ON s.id=i.sale_id "
             "WHERE s.status='OK' GROUP BY 1) t ON t.pid=p.id" + where + f" ORDER BY {SORTS[srt]} LIMIT ?", p + [lim])
    st.caption(f"Menampilkan {len(df)} dari {total} barang · klik **＋ Tambah** untuk memasukkan ke keranjang")
    if df.empty: st.info("Barang tidak ditemukan. Coba kata kunci lain 🔍"); return
    cart, cols = st.session_state.cart, st.columns(3)
    for i, r in enumerate(df.itertuples()):
        with cols[i % 3].container(key=f"pc_{r.id}"):
            st.markdown(card_html(r, cart.get(int(r.id), 0)), unsafe_allow_html=True)
            st.button("＋ Tambah", key=f"add_{r.id}", on_click=cart_add, args=(int(r.id),), disabled=r.stok <= 0, use_container_width=True)
    if total > len(df):
        st.button(f"⬇️ Tampilkan {min(45, total - len(df))} barang lagi", key="cat_more", use_container_width=True,
                  on_click=lambda: st.session_state.update(cat_lim=lim + 45))

def cart_panel():
    cart = st.session_state.cart
    st.markdown(f"<div class='carttitle'>🧾 Keranjang <span class='pill'>{sum(cart.values())}</span></div>", unsafe_allow_html=True)
    if st.session_state.pop("celebrate", False): st.toast("Transaksi berhasil disimpan! 🎉", icon="✅")
    if st.session_state.get("last_sale"):
        sid = st.session_state.last_sale; txt = receipt_text(sid)
        st.success("Transaksi berhasil disimpan — stok & kas sudah diperbarui.")
        st.code(txt, language=None)
        a, b = st.columns(2)
        a.download_button("⬇️ Simpan struk", txt, file_name="struk.txt", use_container_width=True)
        if b.button("✖ Tutup struk", use_container_width=True): st.session_state.last_sale = None; st.rerun()
        components.html(f"<style>@media print{{button{{display:none}}}}</style><pre style='font:13px monospace'>{html.escape(txt)}</pre>"
                        "<button onclick='window.print()' style='padding:8px 16px'>🖨️ Cetak struk</button>", height=120)
        st.divider()
    if not cart:
        st.markdown("<div class='empty'><div class='big'>🛒</div>Keranjang masih kosong<br><small>Scan barcode atau klik barang di katalog 👈</small></div>", unsafe_allow_html=True)
        return
    total, ok = 0, True
    for pid in list(cart):
        p = get_product(pid)
        if not p: cart_del(pid); continue
        k = f"q_{pid}"
        if k not in st.session_state: st.session_state[k] = cart[pid]
        with st.container(key=f"ci_{pid}"):
            src = prod_img(p["nama"], p["kategori"], p["emoji"], p["satuan"], p["gambar"])
            st.markdown(f"<div class='cihead'><img src='{src}' alt=''><div><div class='nm'>{esc(p['nama'])}</div>"
                        f"<div class='sb'>{rp(p['harga_eceran'])} / {esc(p['satuan'] or '')} · sisa stok {p['stok']}</div></div></div>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            c1.button("−", key=f"m{pid}", on_click=cart_step, args=(pid, -1), use_container_width=True)
            qty = int(c2.number_input("Jumlah", min_value=1, step=1, key=k, label_visibility="collapsed"))
            c3.button("＋", key=f"p{pid}", on_click=cart_step, args=(pid, 1), use_container_width=True)
            c4.button("🗑️", key=f"d{pid}", on_click=cart_del, args=(pid,), use_container_width=True)
            cart[pid] = qty
            harga, mode = price_for(p, qty); sub = harga * qty; total += sub
            badge = "<span class='badge-g'>GROSIR AKTIF 🎉</span>" if mode == "GROSIR" else "<span class='badge-e'>Eceran</span>"
            st.markdown(f"{badge} &nbsp; {qty} × {rp(harga)} = **{rp(sub)}**", unsafe_allow_html=True)
            if mode == "ECER" and p["harga_grosir"] and p["min_grosir"]:
                st.caption(f"💡 Beli ≥ {p['min_grosir']} {p['satuan']} → harga grosir {rp(p['harga_grosir'])}")
            if qty > p["stok"]: ok = False; st.error(f"Stok Tidak Mencukupi (sisa {p['stok']} {p['satuan']})")
    if not cart: return
    st.markdown(f"<div class='total'><span><small>TOTAL BAYAR</small><br>{rp(total)}</span><b>{sum(cart.values())} item</b></div>", unsafe_allow_html=True)
    metode = st.radio("Metode bayar", ["Tunai", "QRIS", "Transfer"], horizontal=True, format_func=lambda m: {"Tunai": "💵 Tunai", "QRIS": "📱 QRIS", "Transfer": "🏦 Transfer"}[m])
    bayar = total
    if metode == "Tunai":
        bayar = st.number_input("Uang diterima (Rp)", min_value=0, step=1000, key="bayar")
        st.button("Uang pas", on_click=lambda: st.session_state.update(bayar=int(total)))
        st.metric("Kembalian", rp(max(bayar - total, 0)) if bayar >= total else "Kurang " + rp(total - bayar))
    disabled = (not ok) or (metode == "Tunai" and bayar < total)
    if st.button("💳 Bayar & Cetak Struk", type="primary", use_container_width=True, disabled=disabled):
        try:
            sid = checkout(dict(cart), metode, float(bayar), st.session_state.user["nama"])
            cart_clear(); st.session_state.last_sale = sid; st.session_state.celebrate = True; st.session_state.pop("bayar", None); st.rerun()
        except Exception as e: st.error(str(e))
    st.button("Kosongkan keranjang", on_click=cart_clear, use_container_width=True)

def page_kasir():
    hero_kasir(st.session_state.user)
    promo_ticker()
    foto_status(compact=True)
    f = st.session_state.pop("flash", None)
    if f: getattr(st, f[0])(f[1])
    L, R = st.columns([3, 2], gap="large")
    with L:
        t1, t2 = st.tabs(["📷 Scan Barang", "🖼️ Pilih Gambar"])
        with t1: scan_tab()
        with t2: catalog_tab()
    with R: cart_panel()

# ───────────────────────── Halaman: Stok ─────────────────────────
def stok_status(r): return "HABIS" if r.stok <= 0 else ("MENIPIS" if r.stok <= r.stok_min else "Aman")

def quick_stock(pid, delta):
    """Tombol ➕/➖ cepat di galeri stok (dipanggil sebagai on_click)."""
    p = get_product(pid)
    if not p: return
    try:
        with closing(conn()) as cn:
            move_stock(cn, pid, delta, "MASUK" if delta > 0 else "KELUAR", "Penyesuaian cepat (galeri stok)", st.session_state.user["nama"])
            cn.commit()
        st.session_state.flash_stok = ("success", f"{'➕' if delta > 0 else '➖'} {p['nama']}: {abs(delta)} {p['satuan'] or ''} → stok {p['stok'] + delta}")
    except Exception as e:
        st.session_state.flash_stok = ("error", f"{p['nama']}: {e}")

def page_stok():
    page_head("📦", "Stok Barang", "Pantau, tambah, dan kurangi persediaan toko")
    foto_status()
    f = st.session_state.pop("flash_stok", None)
    if f: st.toast(f[1], icon="✅" if f[0] == "success" else "⚠️")
    owner = st.session_state.user["role"] == "owner"
    df = qdf("SELECT * FROM products WHERE aktif=1 ORDER BY kategori, nama")
    df["status"] = [stok_status(r) for r in df.itertuples()]
    c = st.columns(4)
    c[0].metric("Jenis barang", len(df)); c[1].metric("Menipis", int((df.status == "MENIPIS").sum()))
    c[2].metric("Habis", int((df.status == "HABIS").sum()))
    if owner: c[3].metric("Nilai persediaan (modal)", rp((df.stok * df.harga_beli).sum()))
    krit = df[df.status != "Aman"].sort_values("stok")
    if len(krit):
        nm = ", ".join(f"{esc(r.nama)} ({r.stok})" for r in krit.head(6).itertuples())
        st.markdown(f"<div class='alertbar'>⚠️ <b>{len(krit)} barang perlu restok:</b> {nm}{' …' if len(krit) > 6 else ''}</div>", unsafe_allow_html=True)
    kats = ["Semua"] + daftar_kategori()
    tabs = st.tabs(["📋 Daftar Stok", "🖼️ Galeri Stok (＋/− cepat)", "➕➖ Tambah / Kurang Stok", "🛠️ Kelola Barang", "🕘 Riwayat Mutasi"])
    with tabs[0]:
        f1, f2, f3 = st.columns([2, 1, 1])
        s = f1.text_input("Cari", key="stk_s"); stt = f2.selectbox("Status", ["Semua", "MENIPIS", "HABIS", "Aman"]); kk = f3.selectbox("Kategori", kats, key="stk_k")
        v = df[df.nama.str.contains(s, case=False, regex=False)] if s else df
        if stt != "Semua": v = v[v.status == stt]
        if kk != "Semua": v = v[v.kategori == kk]
        v = v.copy()
        v["foto"] = [thumb_uri(g) for g in v.gambar]
        v["level"] = [stock_pct(int(a), int(b or 0)) for a, b in zip(v.stok, v.stok_min)]
        v["kondisi"] = v.status.map({"HABIS": "🔴 Habis", "MENIPIS": "🟠 Menipis", "Aman": "🟢 Aman"})
        cols = ["foto", "kode", "barcode", "nama", "kategori", "stok", "level", "satuan", "stok_min", "harga_eceran", "harga_grosir", "min_grosir", "kondisi"]
        if owner: cols.insert(cols.index("harga_eceran"), "harga_beli")
        cc = st.column_config
        cfg = {"foto": cc.ImageColumn("Foto", width="small"), "level": cc.ProgressColumn("Level stok", min_value=0, max_value=100, format="%d%%"),
               "harga_eceran": cc.NumberColumn("Harga eceran", format="Rp %d"), "harga_grosir": cc.NumberColumn("Harga grosir", format="Rp %d"),
               "harga_beli": cc.NumberColumn("Harga beli", format="Rp %d")}
        st.dataframe(v[cols], use_container_width=True, hide_index=True, column_config=cfg)
    with tabs[1]:
        st.caption("Tekan **➖ / ➕** di bawah foto barang untuk mengurangi / menambah stok langsung. Atur jumlah per klik di bawah. "
                   "Untuk mencatat pembelian ke kas, pakai tab **Tambah / Kurang Stok**.")
        g1, g2, g3, g4 = st.columns([2, 1, 1, 1])
        gs = g1.text_input("Cari di galeri", key="gal_s", placeholder="ketik nama barang…")
        gk = g2.selectbox("Kategori", kats, key="gal_k"); gt = g3.selectbox("Tampilkan", ["Semua", "MENIPIS", "HABIS", "Aman"], key="gal_t")
        step = int(g4.number_input("Jumlah per klik", min_value=1, max_value=10000, value=1, step=1, key="gal_step"))
        gv = df[df.nama.str.contains(gs, case=False, regex=False)] if gs else df
        if gk != "Semua": gv = gv[gv.kategori == gk]
        if gt != "Semua": gv = gv[gv.status == gt]
        sig = (gs, gk, gt)
        if st.session_state.get("gal_sig") != sig: st.session_state.gal_sig = sig; st.session_state.gal_lim = 40
        lim = st.session_state.get("gal_lim", 40)
        if gv.empty: st.info("Tidak ada barang yang cocok.")
        gc = st.columns(4)
        for i, r in enumerate(gv.head(lim).itertuples()):
            with gc[i % 4].container(key=f"pg_{r.id}"):
                st.markdown(card_html(r), unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                b1.button(f"➖ {step}", key=f"gm_{r.id}", on_click=quick_stock, args=(int(r.id), -step), disabled=int(r.stok) < step, use_container_width=True)
                b2.button(f"➕ {step}", key=f"gp_{r.id}", on_click=quick_stock, args=(int(r.id), step), use_container_width=True)
        if len(gv) > lim:
            st.button(f"⬇️ Tampilkan {min(40, len(gv) - lim)} barang lagi (sisa {len(gv) - lim})", key="gal_more", use_container_width=True,
                      on_click=lambda: st.session_state.update(gal_lim=lim + 40))
    with tabs[2]:
        t1, t2 = st.columns([2, 1])
        ts = t1.text_input("Cari barang", key="tk_s", placeholder="ketik nama barang untuk mempersempit pilihan…")
        tk = t2.selectbox("Kategori", kats, key="tk_k")
        dv = df[df.nama.str.contains(ts, case=False, regex=False)] if ts else df
        if tk != "Semua": dv = dv[dv.kategori == tk]
        if dv.empty: st.info("Barang tidak ditemukan.")
        else:
            opt = {int(r.id): f"{r.nama} ({r.kode}) — stok {r.stok} {r.satuan}" for r in dv.itertuples()}
            pid = st.selectbox("Barang", list(opt), format_func=opt.get, key="tk_pid")
            p = get_product(pid)
            src = prod_img(p["nama"], p["kategori"], "", p["satuan"], p["gambar"])
            warna = "#ef4444" if p["stok"] <= 0 else ("#f59e0b" if p["stok"] <= p["stok_min"] else "#16a34a")
            st.markdown(f"<div style='display:flex;gap:14px;align-items:center;margin:4px 0 10px'><img src='{src}' style='width:120px;border-radius:14px;box-shadow:0 4px 12px rgba(0,0,0,.18)'>"
                        f"<div><div style='font-weight:700;font-size:1.05rem'>{esc(p['nama'])}</div>"
                        f"<div style='color:#64748b;font-size:.85rem'>Stok sekarang: <b style='color:{warna};font-size:1.1rem'>{p['stok']} {esc(p['satuan'] or '')}</b> · batas kritis {p['stok_min']}</div></div></div>", unsafe_allow_html=True)
            aksi = st.radio("Aksi", ["➕ Tambah (barang masuk)", "➖ Kurangi (rusak/hilang/kedaluwarsa)", "🔧 Koreksi stok (stok opname)"], horizontal=True, key="tk_aksi")
            koreksi = aksi.startswith("🔧")
            qty = st.number_input("Stok fisik sebenarnya" if koreksi else "Jumlah", min_value=0, step=1, value=int(p["stok"]) if koreksi else 0, key=f"tk_qty_{pid}_{int(koreksi)}")
            ket = st.text_input("Keterangan", placeholder="mis. restok dari supplier / dus rusak", key="tk_ket")
            catat = False
            if aksi.startswith("➕") and owner: catat = st.checkbox("Catat sebagai pengeluaran kas (harga beli × jumlah)", value=True, key="tk_kas")
            if st.button("Simpan perubahan stok", type="primary", key="tk_save"):
                if qty <= 0 and not koreksi: st.warning("Isi jumlah lebih dari 0.")
                else:
                    try:
                        with closing(conn()) as cn:
                            user = st.session_state.user["nama"]
                            if aksi.startswith("➕"):
                                move_stock(cn, pid, int(qty), "MASUK", ket or "Barang masuk", user)
                                if catat and qty: add_cash(cn, "KELUAR", "Pembelian Stok", p["harga_beli"] * qty, f"{p['nama']} x{qty}", user)
                            elif aksi.startswith("➖"): move_stock(cn, pid, -int(qty), "KELUAR", ket or "Barang keluar", user)
                            else: move_stock(cn, pid, int(qty) - p["stok"], "KOREKSI", ket or "Stok opname", user)
                            cn.commit()
                        st.session_state.flash_stok = ("success", f"Stok {p['nama']} diperbarui.")
                        st.rerun()
                    except Exception as e: st.error(str(e))
    with tabs[3]:
        if not owner: st.info("Hanya Owner yang dapat menambah/mengubah/menghapus data barang.")
        else: form_barang(df)
    with tabs[4]:
        st.dataframe(qdf("SELECT m.waktu,p.nama,m.tipe,m.qty,m.stok_akhir,m.ket,m.user FROM stock_moves m JOIN products p ON p.id=m.product_id "
                         "ORDER BY m.id DESC LIMIT 300"), use_container_width=True, hide_index=True)

SUMBER_LBL = {"f": "Makanan/minuman kemasan (Open Food Facts)", "b": "Perawatan/kebersihan (Open Beauty/Products Facts)",
              "w": "Barang umum (Wikimedia Commons)", "x": "Tanpa foto internet (unggah sendiri)"}

def form_barang(df):
    opt = {0: "➕ Barang baru"} | {int(r.id): f"{r.nama} ({r.kode})" for r in df.itertuples()}
    pid = st.selectbox("Pilih", list(opt), format_func=opt.get, key="kb_sel")
    p = get_product(pid) if pid else None
    if p:
        pv = prod_img(p["nama"], p["kategori"], "", p["satuan"], p["gambar"])
        st.markdown(f"<div style='display:flex;gap:14px;align-items:center;margin:6px 0 10px'><img src='{pv}' style='width:150px;border-radius:14px;box-shadow:0 4px 12px rgba(0,0,0,.18)'>"
                    "<div style='color:#64748b;font-size:.85rem'>Foto saat ini.<br>Foto asli diunduh otomatis dari internet. "
                    "Bisa diganti dengan <b>unggah foto</b> sendiri atau <b>tempel URL gambar</b> di bawah.</div></div>", unsafe_allow_html=True)
        b1, b2, _ = st.columns([1.3, 1, 2])
        if b1.button("🔄 Cari foto otomatis untuk barang ini", key=f"kb_cari_{pid}", use_container_width=True):
            with st.spinner("Mencari foto di internet… (bisa sampai ±20 detik)"):
                try: ok, msg = ambil_foto(pid)
                except NetError: ok, msg = False, "Tidak ada koneksi internet / server sedang sibuk."
            if ok: st.success("Foto ditemukan & disimpan."); st.rerun()
            else: st.warning(f"Belum berhasil: {msg}. Coba tempel URL gambar atau unggah foto sendiri.")
        if p["gambar"] and b2.button("🗑️ Hapus foto", key=f"kb_hf_{pid}", use_container_width=True):
            run("UPDATE products SET gambar='', foto_coba=1 WHERE id=?", (pid,)); st.rerun()
    g = lambda f, d: (p[f] if p and p[f] is not None else d)
    cats = list(dict.fromkeys(KATEGORI + sorted(set(df.kategori.tolist()))))
    with st.form(f"fb_{pid}"):
        a, b = st.columns(2)
        kode = a.text_input("Kode / Barcode", g("kode", "")); nama = b.text_input("Nama barang", g("nama", ""))
        kat = a.selectbox("Kategori", cats, index=cats.index(g("kategori", "Sembako")) if g("kategori", "Sembako") in cats else 0); kat2 = b.text_input("…atau kategori baru")
        sat = a.text_input("Satuan", g("satuan", "pcs"))
        hb = a.number_input("Harga beli / modal", 0, step=500, value=int(g("harga_beli", 0)))
        he = b.number_input("Harga eceran", 0, step=500, value=int(g("harga_eceran", 0)))
        hg = a.number_input("Harga grosir (0 = tanpa grosir)", 0, step=500, value=int(g("harga_grosir", 0)))
        mg = b.number_input("Batas qty grosir", 0, step=1, value=int(g("min_grosir", 0)))
        stok = a.number_input("Stok awal" if not p else "Stok (ubah lewat tab Tambah/Kurang)", 0, step=1, value=int(g("stok", 0)), disabled=bool(p))
        smin = b.number_input("Batas stok kritis", 0, step=1, value=int(g("stok_min", 5)))
        st.markdown("**Foto barang**")
        up = st.file_uploader("Unggah foto sendiri (opsional)", type=["png", "jpg", "jpeg", "webp"])
        url = st.text_input("…atau tempel URL gambar (opsional)", g("gambar_url", ""), placeholder="https://…/foto.jpg")
        d1, d2 = st.columns(2)
        cari = d1.text_input("Kata kunci cari foto otomatis", g("kata_cari", ""), help="Pisahkan alternatif dengan |  ·  Tambahkan || lalu kata kunci bahasa Inggris untuk Wikimedia. Contoh: indomie mi goreng")
        skeys = list(SUMBER_LBL)
        src = d2.selectbox("Sumber foto otomatis", skeys, index=skeys.index(g("sumber", "f")) if g("sumber", "f") in skeys else 0, format_func=SUMBER_LBL.get)
        save = st.form_submit_button("💾 Simpan", type="primary")
    if save:
        if not kode or not nama: st.error("Kode dan nama wajib diisi."); return
        if hg and hg >= he: st.warning("Harga grosir sebaiknya lebih rendah dari eceran.")
        img = g("gambar", "")
        if up:
            try: img = simpan_foto("upload", up.getvalue())
            except Exception as e: st.error(f"Foto tidak bisa dibaca: {e}"); return
        elif url.strip() and url.strip() != g("gambar_url", ""):
            try: img = simpan_foto("url", http_get(url.strip()))
            except NetError: st.warning("Tidak ada koneksi internet — foto dari URL belum diunduh.")
            except Exception as e: st.warning(f"Foto dari URL gagal dipakai: {e}")
        kat = kat2.strip() or kat
        try:
            if p:
                run("UPDATE products SET kode=?,nama=?,kategori=?,gambar=?,satuan=?,harga_beli=?,harga_eceran=?,harga_grosir=?,min_grosir=?,stok_min=?,"
                    "gambar_url=?,kata_cari=?,sumber=? WHERE id=?", (kode, nama, kat, img, sat, hb, he, hg, mg, smin, url.strip(), cari.strip(), src, pid))
                if not img: run("UPDATE products SET foto_coba=0 WHERE id=?", (pid,))
            else:
                new = run("INSERT INTO products(kode,nama,kategori,emoji,gambar,satuan,harga_beli,harga_eceran,harga_grosir,min_grosir,stok,stok_min,gambar_url,kata_cari,sumber,foto_coba) "
                          "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)", (kode, nama, kat, "", img, sat, hb, he, hg, mg, stok, smin, url.strip(), cari.strip() or nama, src))
                run("INSERT INTO stock_moves(waktu,product_id,tipe,qty,stok_akhir,ket,user) VALUES(?,?,?,?,?,?,?)", (now(), new, "AWAL", stok, stok, "Barang baru", st.session_state.user["nama"]))
            ensure_barcode(pid if p else new)
            mulai_unduh_foto()
            st.success("Tersimpan."); st.rerun()
        except sqlite3.IntegrityError: st.error("Kode barang sudah dipakai.")
    if p:
        with st.expander("🏷️ Barcode & cetak"):
            if p["barcode"]:
                st.caption(f"Barcode EAN-13: `{p['barcode']}` — tempel di kemasan, lalu scan di kasir.")
                try:
                    png = barcode_png(p["barcode"]); st.image(png, width=300)
                    st.download_button("⬇️ Unduh PNG", png, file_name=f"barcode_{p['barcode']}.png", mime="image/png", key=f"bc_{pid}")
                except ImportError: st.error("Jalankan: pip install python-barcode pillow")
            else: st.info(f"Barcode otomatis dibuat untuk barang dengan harga eceran ≥ {rp(HARGA_BARCODE_MIN)}.")
    if p and st.button("🗑️ Hapus barang ini (nonaktifkan)"):
        run("UPDATE products SET aktif=0, kode=kode||'#del'||id WHERE id=?", (pid,)); st.rerun()

# ───────────────────────── Periode & Dashboard ─────────────────────────
def pilih_periode(key):
    o = st.selectbox("Periode", ["Hari ini", "7 hari terakhir", "30 hari terakhir", "Bulan ini", "Semua", "Pilih tanggal"], key=key)
    t = today()
    if o == "Hari ini": return t, t
    if o == "7 hari terakhir": return t - dt.timedelta(days=6), t
    if o == "30 hari terakhir": return t - dt.timedelta(days=29), t
    if o == "Bulan ini": return t.replace(day=1), t
    if o == "Semua": return dt.date(2000, 1, 1), t
    r = st.date_input("Rentang", (t - dt.timedelta(days=6), t), key=key + "d")
    return (r[0], r[1]) if len(r) == 2 else (t, t)

def page_dashboard():
    page_head("📊", "Dashboard & Laporan", "Omset, modal, untung, dan barang terlaris")
    d1, d2 = pilih_periode("per_d"); P = (str(d1), str(d2))
    s = qdf("SELECT * FROM sales WHERE status='OK' AND date(waktu) BETWEEN ? AND ?", P)
    omset, modal = s.total.sum(), s.modal.sum()
    c = st.columns(5)
    c[0].metric("Omset", rp(omset)); c[1].metric("Modal (HPP)", rp(modal)); c[2].metric("Untung", rp(omset - modal))
    c[3].metric("Margin", f"{(omset - modal) / omset * 100:.1f}%" if omset else "0%"); c[4].metric("Jumlah transaksi", len(s))
    t1, t2, t3 = st.tabs(["📈 Grafik", "⚠️ Stok Kritis", "🧾 Riwayat Penjualan"])
    with t1:
        if s.empty: st.info("Belum ada penjualan pada periode ini.")
        else:
            s["tgl"] = s.waktu.str[:10]; s["jam"] = s.waktu.str[11:13]
            it = qdf("SELECT i.* FROM sale_items i JOIN sales s ON s.id=i.sale_id WHERE s.status='OK' AND date(s.waktu) BETWEEN ? AND ?", P)
            top = it.groupby("nama").qty.sum().nlargest(5)
            if len(top):
                st.markdown("<div class='sech'>🏆 Barang Terlaris</div>", unsafe_allow_html=True)
                pm = qdf("SELECT nama,kategori,emoji,satuan,gambar FROM products ORDER BY aktif DESC, id DESC").drop_duplicates("nama").set_index("nama")
                rc = st.columns(5)
                for i, (nm, q) in enumerate(top.items()):
                    if nm in pm.index: m = pm.loc[nm]; src_img, sat = prod_img(nm, m.kategori, m.emoji, m.satuan, m.gambar), m.satuan
                    else: src_img, sat = product_art(nm, "", "📦", ""), ""
                    rc[i].markdown(f"<div class='rank'><span class='md'>{['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i]}</span><img src='{src_img}' alt=''>"
                                   f"<div class='nm'>{esc(nm)}</div><div class='sv'>{int(q)} {esc(str(sat or ''))} terjual</div></div>", unsafe_allow_html=True)
            a, b = st.columns(2)
            a.subheader("Omset, modal & untung harian")
            a.bar_chart(s.groupby("tgl")[["total", "modal", "untung"]].sum().rename(columns={"total": "Omset", "modal": "Modal", "untung": "Untung"}), color=["#0ea5e9", "#f59e0b", "#16a34a"])
            b.subheader("Jam sibuk (jumlah transaksi)")
            b.bar_chart(s.groupby("jam").size().rename("Transaksi"), color="#f59e0b")
            a, b = st.columns(2)
            a.subheader("10 barang terlaris")
            a.bar_chart(it.groupby("nama").qty.sum().nlargest(10), color="#16a34a")
            b.subheader("Untung per kategori")
            it["untung"] = it.subtotal - it.modal
            b.bar_chart(it.groupby("kategori").untung.sum(), color="#a855f7")
    with t2:
        k = qdf("SELECT kode,nama,kategori,stok,satuan,stok_min FROM products WHERE aktif=1 AND stok<=stok_min ORDER BY stok")
        st.dataframe(k, use_container_width=True, hide_index=True) if len(k) else st.success("Semua stok aman.")
    with t3:
        h = qdf("SELECT id,nota,waktu,kasir,total,modal,untung,metode,status FROM sales WHERE date(waktu) BETWEEN ? AND ? ORDER BY id DESC", P)
        st.dataframe(h.drop(columns="id"), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Unduh CSV", h.to_csv(index=False), file_name="penjualan.csv")
        if len(h):
            sel = st.selectbox("Lihat detail nota", h.id.tolist(), format_func=lambda i: h.set_index("id").loc[i, "nota"])
            st.code(receipt_text(int(sel)), language=None)
            if h.set_index("id").loc[sel, "status"] == "OK" and st.button("❌ Batalkan transaksi ini (stok dikembalikan)"):
                try: void_sale(int(sel), st.session_state.user["nama"]); st.success("Dibatalkan."); st.rerun()
                except Exception as e: st.error(str(e))

# ───────────────────────── Halaman: Keuangan ─────────────────────────
def page_keuangan():
    page_head("💵", "Pemantauan Keuangan", "Pemasukan, pengeluaran, dan saldo kas")
    d1, d2 = pilih_periode("per_k"); P = (str(d1), str(d2))
    df = qdf("SELECT * FROM cash WHERE date(waktu) BETWEEN ? AND ? ORDER BY id DESC", P)
    masuk = df[df.tipe == "MASUK"].nominal.sum(); keluar = df[df.tipe == "KELUAR"].nominal.sum()
    saldo = qdf("SELECT COALESCE(SUM(CASE WHEN tipe='MASUK' THEN nominal ELSE -nominal END),0) s FROM cash")["s"][0]
    c = st.columns(4)
    c[0].metric("Pemasukan", rp(masuk)); c[1].metric("Pengeluaran", rp(keluar)); c[2].metric("Selisih periode", rp(masuk - keluar)); c[3].metric("Saldo kas total", rp(saldo))
    with st.expander("➕➖ Tambah / kurangi catatan kas", expanded=True):
        a, b, cc = st.columns([1, 1, 1])
        tipe = a.radio("Jenis", ["➕ Pemasukan", "➖ Pengeluaran"], horizontal=True)
        kat = b.selectbox("Kategori", ["Modal Awal", "Setoran Modal", "Pendapatan Lain"] if tipe.startswith("➕")
                          else ["Pembelian Stok", "Gaji", "Listrik/Air", "Sewa", "Transportasi", "Prive", "Lain-lain"])
        nom = cc.number_input("Nominal (Rp)", min_value=0, step=5000)
        ket = st.text_input("Keterangan", key="kas_ket")
        if st.button("Simpan catatan kas", type="primary") and nom > 0:
            with closing(conn()) as cn:
                add_cash(cn, "MASUK" if tipe.startswith("➕") else "KELUAR", kat, nom, ket, st.session_state.user["nama"]); cn.commit()
            st.rerun()
    st.subheader("Transaksi keuangan")
    st.dataframe(df.drop(columns=["sale_id"]), use_container_width=True, hide_index=True)
    st.download_button("⬇️ Unduh CSV", df.to_csv(index=False), file_name="kas.csv")
    man = df[df.sale_id.isna()]
    if len(man):
        hid = st.selectbox("Hapus catatan manual", man.id.tolist(), format_func=lambda i: f"#{i} {man.set_index('id').loc[i, 'kategori']} {rp(man.set_index('id').loc[i, 'nominal'])}")
        if st.button("🗑️ Hapus catatan"): run("DELETE FROM cash WHERE id=?", (int(hid),)); st.rerun()

# ───────────────────────── Halaman: Pengaturan ─────────────────────────
def page_pengaturan():
    page_head("⚙️", "Pengaturan", "Toko, pengguna, dan data")
    t1, t2, t3 = st.tabs(["🏪 Toko & Struk", "👥 Pengguna", "💾 Data"])
    with t1:
        with st.form("toko"):
            tk = st.text_input("Nama toko", setting("toko")); al = st.text_input("Alamat", setting("alamat")); ft = st.text_input("Footer struk", setting("footer"))
            if st.form_submit_button("Simpan"):
                for k, v in (("toko", tk), ("alamat", al), ("footer", ft)): run("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, v))
                st.success("Tersimpan.")
    with t2:
        u = qdf("SELECT id,username,nama,role FROM users"); st.dataframe(u, hide_index=True, use_container_width=True)
        with st.form("usr"):
            a, b, c, d = st.columns(4)
            un = a.text_input("Username"); nm = b.text_input("Nama"); rl = c.selectbox("Peran", ["kasir", "owner"]); pw = d.text_input("Password", type="password")
            if st.form_submit_button("➕ Tambah / reset password"):
                if un and pw and nm:
                    ex = one("SELECT id FROM users WHERE username=?", (un,))
                    if ex: run("UPDATE users SET nama=?,role=?,pw=? WHERE id=?", (nm, rl, hash_pw(pw), ex["id"]))
                    else: run("INSERT INTO users(username,nama,role,pw) VALUES(?,?,?,?)", (un, nm, rl, hash_pw(pw)))
                    st.success("Tersimpan."); st.rerun()
                else: st.error("Lengkapi semua kolom.")
        dl = st.selectbox("Hapus pengguna", u.username.tolist())
        if st.button("🗑️ Hapus pengguna"):
            if dl == st.session_state.user["username"]: st.error("Tidak bisa menghapus akun sendiri.")
            else: run("DELETE FROM users WHERE username=?", (dl,)); st.rerun()
    with t3:
        if os.path.exists(DB): st.download_button("⬇️ Backup database", open(DB, "rb").read(), file_name="backup_bulojaya.db")
        st.warning("Hapus semua riwayat transaksi, kas & mutasi (data barang & stok tetap). Gunakan setelah uji coba, sebelum dipakai sungguhan.")
        if st.text_input("Ketik HAPUS untuk konfirmasi") == "HAPUS" and st.button("Hapus riwayat transaksi"):
            for t in ("sales", "sale_items", "cash", "stock_moves"): run(f"DELETE FROM {t}")
            st.success("Riwayat dihapus.")

# ───────────────────────── Login & Navigasi ─────────────────────────
def login():
    _, m, _ = st.columns([1, 1.1, 1])
    with m:
        with st.container(key="loginbox"):
            st.markdown("<div class='login-hero'><div class='logo'>🛒</div><div class='brand'>POS Bulo Jaya</div><div class='tag'>Sistem kasir &amp; persediaan UMKM</div>"
                        "<div class='er'>🍚🥚☕🍜🧼🛢️</div></div>", unsafe_allow_html=True)
            with st.form("login"):
                u = st.text_input("Username"); p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk", type="primary", use_container_width=True):
                    r = one("SELECT * FROM users WHERE username=?", (u.strip(),))
                    if r and check_pw(p, r["pw"]):
                        st.session_state.user = dict(r)
                        st.session_state.cart = load_cart(r["username"]); st.session_state.cart_saved = dict(st.session_state.cart)
                        st.rerun()
                    else: st.error("Username atau password salah.")
            st.caption("Akun awal → owner / owner123  ·  kasir1, kasir2, kasir3 / kasir123  (ganti di menu Pengaturan)")

def main():
    init_db()
    st.session_state.setdefault("cart", {})
    if "user" not in st.session_state: return login()
    mulai_unduh_foto()
    u = st.session_state.user
    pages = {"🛒 Kasir": page_kasir, "📦 Stok Barang": page_stok}
    if u["role"] == "owner": pages |= {"📊 Dashboard & Laporan": page_dashboard, "💵 Keuangan": page_keuangan, "⚙️ Pengaturan": page_pengaturan}
    with st.sidebar:
        st.markdown(f"<div class='brand-side'><div class='logo'>🛒</div><div><div class='bn'>{esc(setting('toko'))}</div><div class='bs'>Kasir &amp; Persediaan</div></div></div>"
                    f"<div class='userchip'>👤 {esc(u['nama'])} · {esc(u['role'])}</div>", unsafe_allow_html=True)
        pg = st.radio("Menu", list(pages), label_visibility="collapsed")
        if st.button("Keluar", use_container_width=True): st.session_state.clear(); st.rerun()
    try: pages[pg]()
    finally: save_cart()  # simpan keranjang ke database setiap ada perubahan

if __name__ == "__main__":
    main()
