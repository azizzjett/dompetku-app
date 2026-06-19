# 💰 Dompetku — Personal Finance Tracker

Aplikasi manajemen keuangan pribadi berbasis web yang terintegrasi dengan Google Sheets secara **realtime**. Dibangun dengan Python, Streamlit, dan Plotly.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-API-green?style=flat-square&logo=googlesheets)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## ✨ Fitur Utama

- **📊 Dashboard Realtime** — Saldo, total pendapatan, dan pengeluaran langsung dari Google Sheets
- **📈 Visualisasi Interaktif** — Grafik tren harian, perbandingan bulanan, dan alokasi kategori (Plotly)
- **➕ Tambah Transaksi** — Input langsung via form, sinkron otomatis ke Google Sheets
- **🗑️ Hapus Transaksi** — Hapus data langsung dari aplikasi menggunakan Google Sheets API
- **🔍 Filter Data** — Filter berdasarkan jenis (Pendapatan/Pengeluaran) dan kategori
- **💡 Rasio Tabungan** — Kalkulasi otomatis persentase tabungan dari total pendapatan
- **🔐 Login System** — Autentikasi admin sebelum akses dashboard

---

## 🖼️ Screenshot

> *Drag & drop screenshot aplikasimu ke sini setelah README ini tersimpan*

---

## 🚀 Demo Live

🔗 **[Coba Aplikasi](https://dompetku-app-fmnapw855lmwsj9sqvhgae.streamlit.app/)**

---

## 🛠️ Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend & Backend | Python + Streamlit |
| Visualisasi | Plotly Express & Graph Objects |
| Database | Google Sheets (via CSV publish & API) |
| Autentikasi | Google Service Account (OAuth2) |
| Deploy | Streamlit Community Cloud |

---

## ⚙️ Cara Menjalankan Lokal

### 1. Clone repo
```bash
git clone https://github.com/azizzjett/dompetku-app.git
cd dompetku-app
```

### 2. Install dependensi
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Google Sheets

Buat file `.streamlit/secrets.toml` dan isi dengan kredensial Google Service Account:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

### 4. Jalankan aplikasi
```bash
streamlit run app.py
```

Buka browser di `http://localhost:8501`

---

## 📁 Struktur Proyek

```
dompetku-app/
├── app.py              # Aplikasi utama
├── apps.py             # Modul pendukung
├── requirements.txt    # Daftar dependensi
└── .devcontainer/      # Konfigurasi dev container
```

---

## 👤 Developer

**Abdul Aziz** — Self-taught developer dari Indonesia.

- 🌐 Portfolio: [abdulazizzblog.gt.tc](http://abdulazizzblog.gt.tc)
- 💼 GitHub: [@azizzjett](https://github.com/azizzjett)

---

## 📄 Lisensi

MIT License — bebas digunakan dan dimodifikasi dengan menyertakan kredit.
