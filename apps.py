import streamlit as st
import pandas as pd
from datetime import datetime, date
import requests
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# =================================================================
# 1. KONFIGURASI UTAMA
# =================================================================
DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vREdDOrXtztLOHd-Km9QDgjjjhzbmMS7J5VYlgknK9Y5Rm47Yf0nHey-Gt3MBiADuUQRtVagLIG1w8h/pub?gid=535445139&single=true&output=csv"
SPREADSHEET_ID = "13cCNY4oFDgGKimLgLRRiz0RLTCiy8z_qkeD5mtNmxKM"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeRTFqYWhRkGMwvBvUqsgz7RWfQUw36JuLuPjcdnGnu09-9ug/formResponse"

st.set_page_config(page_title="Dompetku Premium", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. SISTEM LOGIN
# =================================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def cek_login(username, password):
    try:
        users = st.secrets["users"]
        if username in users:
            return users[username] == hash_password(password)
        return False
    except:
        return username == "admin" and password == "dompetku123"

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin-bottom:30px;'>
            <h1>💰 Dompetku</h1>
            <p style='color:gray;'>Sistem Pelacak Keuangan Pribadi</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("form_login"):
            st.markdown("### 🔐 Masuk ke Akun Anda")
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            tombol_login = st.form_submit_button("🚀 Login", use_container_width=True)
        if tombol_login:
            if cek_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("❌ Username atau password salah!")
        st.info("💡 Default: username `admin` / password `dompetku123`")
    st.stop()

# =================================================================
# 3. GOOGLE SHEETS API
# =================================================================
def get_gsheet_client():
    try:
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        return gspread.authorize(creds)
    except:
        return None

def get_or_create_sheet(spreadsheet, nama_sheet):
    """Ambil sheet jika ada, buat baru jika belum ada."""
    try:
        return spreadsheet.worksheet(nama_sheet)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=nama_sheet, rows=1000, cols=10)
        # Tambah header
        if nama_sheet == "Pendapatan":
            sheet.append_row(["Timestamp", "Kategori", "Jumlah", "Catatan"])
        elif nama_sheet == "Rekap":
            sheet.append_row(["Bulan", "Total Pengeluaran", "Jumlah Transaksi"])
        else:  # Sheet pengeluaran bulanan
            sheet.append_row(["Timestamp", "Kategori", "Jumlah", "Catatan"])
        return sheet

def pindahkan_data_ke_sheet_baru(client):
    """
    Baca semua data dari Form_Responses lama,
    pisahkan ke sheet Pendapatan dan Pengeluaran_YYYY_MM.
    """
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        # Baca sheet lama
        try:
            sheet_lama = spreadsheet.worksheet("Form_Responses")
        except:
            try:
                sheet_lama = spreadsheet.worksheet("Form Responses 1")
            except:
                return False, "Sheet sumber tidak ditemukan"

        data_lama = sheet_lama.get_all_records()
        if not data_lama:
            return False, "Data kosong"

        df = pd.DataFrame(data_lama)
        if 'Timestamp' in df.columns:
            df['Tanggal'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Pisahkan dan tulis ke sheet baru
        for _, row in df.iterrows():
            tgl = row.get('Tanggal', datetime.now())
            jenis = str(row.get('Jenis', '')).strip()
            kategori = str(row.get('Kategori', '')).strip()
            jumlah = row.get('Jumlah', 0)
            catatan = str(row.get('Catatan', '')).strip()
            timestamp = str(row.get('Timestamp', ''))

            if jenis == 'Pendapatan':
                sheet = get_or_create_sheet(spreadsheet, "Pendapatan")
                sheet.append_row([timestamp, kategori, jumlah, catatan])
            elif jenis == 'Pengeluaran':
                if pd.notna(tgl):
                    nama_sheet = f"Pengeluaran_{tgl.strftime('%Y_%m')}"
                else:
                    nama_sheet = f"Pengeluaran_{datetime.now().strftime('%Y_%m')}"
                sheet = get_or_create_sheet(spreadsheet, nama_sheet)
                sheet.append_row([timestamp, kategori, jumlah, catatan])

        return True, "Berhasil"
    except Exception as e:
        return False, str(e)

def hapus_baris(nama_sheet, nomor_baris):
    try:
        client = get_gsheet_client()
        if not client:
            return False, "Service account belum dikonfigurasi"
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(nama_sheet)
        sheet.delete_rows(nomor_baris)
        return True, "Berhasil"
    except Exception as e:
        return False, str(e)

def tambah_transaksi_ke_sheet(jenis, kategori, jumlah, catatan):
    """Tambah transaksi langsung ke sheet yang sesuai via API."""
    try:
        client = get_gsheet_client()
        if not client:
            return False, "Service account belum dikonfigurasi"
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if jenis == 'Pendapatan':
            sheet = get_or_create_sheet(spreadsheet, "Pendapatan")
        else:
            nama_sheet = f"Pengeluaran_{datetime.now().strftime('%Y_%m')}"
            sheet = get_or_create_sheet(spreadsheet, nama_sheet)

        sheet.append_row([timestamp, kategori, jumlah, catatan])
        return True, "Berhasil"
    except Exception as e:
        return False, str(e)

def update_rekap_bulanan(client=None):
    """Update sheet Rekap dengan total pengeluaran per bulan."""
    try:
        if not client:
            client = get_gsheet_client()
        if not client:
            return
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        semua_sheet = [s.title for s in spreadsheet.worksheets()]
        sheet_pengeluaran = sorted([s for s in semua_sheet if s.startswith("Pengeluaran_")])

        rekap_data = []
        for nama in sheet_pengeluaran:
            sh = spreadsheet.worksheet(nama)
            records = sh.get_all_records()
            if records:
                df = pd.DataFrame(records)
                if 'Jumlah' in df.columns:
                    total = pd.to_numeric(df['Jumlah'], errors='coerce').fillna(0).sum()
                    bulan_str = nama.replace("Pengeluaran_", "").replace("_", "-")
                    rekap_data.append([bulan_str, total, len(df)])

        if rekap_data:
            sheet_rekap = get_or_create_sheet(spreadsheet, "Rekap")
            sheet_rekap.clear()
            sheet_rekap.append_row(["Bulan", "Total Pengeluaran", "Jumlah Transaksi"])
            for row in rekap_data:
                sheet_rekap.append_row(row)
    except:
        pass

# =================================================================
# 4. FUNGSI BACA DATA DARI SEMUA SHEET
# =================================================================
@st.cache_data(ttl=15)
def muat_semua_data():
    """Baca data dari sheet Pendapatan + semua sheet Pengeluaran_YYYY_MM."""
    try:
        # Untuk membaca publik, kita pakai URL CSV sheet per sheet
        # Daftar sheet yang ada kita ambil via gspread jika ada service account
        hasil = {
            "pendapatan": pd.DataFrame(),
            "pengeluaran": {},  # dict {nama_sheet: df}
            "rekap": pd.DataFrame(),
            "sumber": "baru"  # flag apakah pakai sheet baru atau lama
        }

        # Coba baca via gspread (butuh service account)
        try:
            scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            semua_sheet = [s.title for s in spreadsheet.worksheets()]

            # Baca Pendapatan
            if "Pendapatan" in semua_sheet:
                records = spreadsheet.worksheet("Pendapatan").get_all_records()
                if records:
                    df = pd.DataFrame(records)
                    df['Tanggal'] = pd.to_datetime(df.get('Timestamp', pd.Series()), errors='coerce')
                    df['Jumlah'] = pd.to_numeric(df.get('Jumlah', 0), errors='coerce').fillna(0)
                    hasil["pendapatan"] = df

            # Baca semua sheet Pengeluaran_YYYY_MM
            sheet_pengeluaran = sorted([s for s in semua_sheet if s.startswith("Pengeluaran_")])
            for nama in sheet_pengeluaran:
                records = spreadsheet.worksheet(nama).get_all_records()
                if records:
                    df = pd.DataFrame(records)
                    df['Tanggal'] = pd.to_datetime(df.get('Timestamp', pd.Series()), errors='coerce')
                    df['Jumlah'] = pd.to_numeric(df.get('Jumlah', 0), errors='coerce').fillna(0)
                    df['_baris_sheet'] = range(2, len(df) + 2)
                    df['_nama_sheet'] = nama
                    hasil["pengeluaran"][nama] = df

            # Baca Rekap
            if "Rekap" in semua_sheet:
                records = spreadsheet.worksheet("Rekap").get_all_records()
                if records:
                    hasil["rekap"] = pd.DataFrame(records)

            return hasil, None

        except Exception as e_api:
            # Fallback: baca dari URL CSV publik (sheet lama)
            df_lama = pd.read_csv(DATA_URL)
            if 'Timestamp' in df_lama.columns:
                df_lama = df_lama.rename(columns={'Timestamp': 'Tanggal'})
            df_lama['Tanggal'] = pd.to_datetime(df_lama['Tanggal'], errors='coerce')
            df_lama['Jumlah'] = pd.to_numeric(df_lama.get('Jumlah', 0), errors='coerce').fillna(0)
            df_lama['_baris_sheet'] = range(2, len(df_lama) + 2)

            hasil["pendapatan"] = df_lama[df_lama.get('Jenis', '') == 'Pendapatan'] if 'Jenis' in df_lama.columns else pd.DataFrame()
            df_pengeluaran = df_lama[df_lama['Jenis'] == 'Pengeluaran'] if 'Jenis' in df_lama.columns else pd.DataFrame()

            if not df_pengeluaran.empty:
                df_pengeluaran['Bulan'] = df_pengeluaran['Tanggal'].dt.strftime('%Y_%m')
                for bulan, grp in df_pengeluaran.groupby('Bulan'):
                    nama = f"Pengeluaran_{bulan}"
                    grp = grp.copy()
                    grp['_nama_sheet'] = nama
                    hasil["pengeluaran"][nama] = grp

            hasil["sumber"] = "lama"
            return hasil, str(e_api)

    except Exception as e:
        return {"pendapatan": pd.DataFrame(), "pengeluaran": {}, "rekap": pd.DataFrame(), "sumber": "error"}, str(e)

# =================================================================
# 5. HEADER + SIDEBAR
# =================================================================
st.title("💰 Dompetku Realtime Monitoring")
st.caption("Sistem Pelacak Keuangan Pribadi — Terintegrasi Google Sheets")
st.markdown("---")

data, error_load = muat_semua_data()
df_pendapatan = data["pendapatan"]
dict_pengeluaran = data["pengeluaran"]
df_rekap = data["rekap"]

# Gabungkan semua pengeluaran untuk ringkasan
df_pengeluaran_all = pd.concat(dict_pengeluaran.values(), ignore_index=True) if dict_pengeluaran else pd.DataFrame()

with st.sidebar:
    st.markdown(f"### 👤 Halo, {st.session_state.get('username', 'User')}!")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("### ⚙️ Panel Kontrol")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**Status**")
    if error_load and data["sumber"] == "error":
        st.error(f"❌ {error_load}")
    elif data["sumber"] == "lama":
        st.warning("⚠️ Membaca dari sheet lama")
        st.info("Klik 'Migrasi Data' di tab Pengaturan untuk memisahkan sheet")
    else:
        total_p = len(df_pendapatan)
        total_e = sum(len(v) for v in dict_pengeluaran.values())
        st.success(f"✅ {total_p} pendapatan | {total_e} pengeluaran")

    try:
        _ = st.secrets["gcp_service_account"]
        st.success("🔑 Service Account: Aktif")
    except:
        st.warning("🔑 Service Account: Nonaktif")

    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

# =================================================================
# 6. HITUNG RINGKASAN
# =================================================================
total_pendapatan = df_pendapatan['Jumlah'].sum() if not df_pendapatan.empty and 'Jumlah' in df_pendapatan.columns else 0
total_pengeluaran = df_pengeluaran_all['Jumlah'].sum() if not df_pengeluaran_all.empty and 'Jumlah' in df_pengeluaran_all.columns else 0
sisa_saldo = total_pendapatan - total_pengeluaran
rasio_hemat = (sisa_saldo / total_pendapatan * 100) if total_pendapatan > 0 else 0

# Kartu ringkasan
st.subheader("📊 Ringkasan Saldo Keseluruhan")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div style='background:linear-gradient(135deg,#28a745,#20c863);padding:20px;border-radius:12px;color:white;'>
        <p style='margin:0;font-size:13px;opacity:0.9;'>🟩 TOTAL PENDAPATAN</p>
        <h2 style='margin:5px 0 0 0;font-size:24px;'>Rp {total_pendapatan:,.0f}</h2>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div style='background:linear-gradient(135deg,#dc3545,#ff4d5e);padding:20px;border-radius:12px;color:white;'>
        <p style='margin:0;font-size:13px;opacity:0.9;'>🟥 TOTAL PENGELUARAN</p>
        <h2 style='margin:5px 0 0 0;font-size:24px;'>Rp {total_pengeluaran:,.0f}</h2>
    </div>""", unsafe_allow_html=True)
with k3:
    warna = "linear-gradient(135deg,#007bff,#0056b3)" if sisa_saldo >= 0 else "linear-gradient(135deg,#fd7e14,#e65c00)"
    st.markdown(f"""<div style='background:{warna};padding:20px;border-radius:12px;color:white;'>
        <p style='margin:0;font-size:13px;opacity:0.9;'>🧮 SISA SALDO BERSIH</p>
        <h2 style='margin:5px 0 0 0;font-size:24px;'>Rp {sisa_saldo:,.0f}</h2>
    </div>""", unsafe_allow_html=True)
with k4:
    warna_r = "linear-gradient(135deg,#6f42c1,#5a2d8a)" if rasio_hemat >= 20 else "linear-gradient(135deg,#ffc107,#e0a800)"
    st.markdown(f"""<div style='background:{warna_r};padding:20px;border-radius:12px;color:white;'>
        <p style='margin:0;font-size:13px;opacity:0.9;'>💡 RASIO TABUNGAN</p>
        <h2 style='margin:5px 0 0 0;font-size:24px;'>{rasio_hemat:.1f}%</h2>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =================================================================
# 7. TABS UTAMA
# =================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Dashboard", "🟩 Pendapatan", "🟥 Pengeluaran per Bulan", "🗑️ Hapus", "⚙️ Pengaturan"
])

# ----------------------------------------------------------------
# TAB 1: DASHBOARD
# ----------------------------------------------------------------
with tab1:
    st.subheader("📈 Grafik Keuangan")

    if not df_pengeluaran_all.empty or not df_pendapatan.empty:
        g1, g2 = st.columns([2, 1])

        with g1:
            st.markdown("**Tren Pendapatan vs Pengeluaran**")
            rows = []
            if not df_pendapatan.empty and 'Tanggal' in df_pendapatan.columns:
                for _, r in df_pendapatan.iterrows():
                    rows.append({'Tanggal': r['Tanggal'], 'Jumlah': r['Jumlah'], 'Jenis': 'Pendapatan'})
            if not df_pengeluaran_all.empty and 'Tanggal' in df_pengeluaran_all.columns:
                for _, r in df_pengeluaran_all.iterrows():
                    rows.append({'Tanggal': r['Tanggal'], 'Jumlah': r['Jumlah'], 'Jenis': 'Pengeluaran'})

            if rows:
                df_gabung = pd.DataFrame(rows)
                df_gabung['Hari'] = df_gabung['Tanggal'].dt.strftime('%Y-%m-%d')
                df_tren = df_gabung.groupby(['Hari', 'Jenis'])['Jumlah'].sum().reset_index()
                df_tren = df_tren.pivot(index='Hari', columns='Jenis', values='Jumlah').fillna(0).reset_index()
                for col in ['Pendapatan', 'Pengeluaran']:
                    if col not in df_tren.columns:
                        df_tren[col] = 0

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_tren['Hari'], y=df_tren['Pendapatan'],
                    mode='lines+markers', name='Pendapatan', line=dict(color='#28a745', width=3),
                    fill='tozeroy', fillcolor='rgba(40,167,69,0.1)'))
                fig.add_trace(go.Scatter(x=df_tren['Hari'], y=df_tren['Pengeluaran'],
                    mode='lines+markers', name='Pengeluaran', line=dict(color='#dc3545', width=3),
                    fill='tozeroy', fillcolor='rgba(220,53,69,0.1)'))
                fig.update_layout(height=320, hovermode="x unified",
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", y=1.1), margin=dict(t=20,b=20))
                fig.update_yaxes(tickprefix="Rp ", tickformat=",.0f")
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            st.markdown("**Alokasi Pengeluaran**")
            if not df_pengeluaran_all.empty and 'Kategori' in df_pengeluaran_all.columns:
                df_pie = df_pengeluaran_all.groupby('Kategori')['Jumlah'].sum().reset_index()
                fig_pie = px.pie(df_pie, values='Jumlah', names='Kategori', hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set3)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(showlegend=False, height=320, margin=dict(t=20,b=20),
                    paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)

        # Grafik rekap bulanan pengeluaran
        st.markdown("**📊 Total Pengeluaran per Bulan**")
        if dict_pengeluaran:
            rekap_list = []
            for nama, df in dict_pengeluaran.items():
                bulan = nama.replace("Pengeluaran_", "").replace("_", "-")
                total = df['Jumlah'].sum() if 'Jumlah' in df.columns else 0
                rekap_list.append({'Bulan': bulan, 'Total': total})
            df_rekap_chart = pd.DataFrame(rekap_list).sort_values('Bulan')

            fig_bulan = px.bar(df_rekap_chart, x='Bulan', y='Total',
                color_discrete_sequence=['#dc3545'], text_auto=True)
            fig_bulan.update_traces(texttemplate='Rp %{y:,.0f}', textposition='outside', textfont_size=10)
            fig_bulan.update_layout(height=300, plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=30,b=20),
                yaxis_title="Total Pengeluaran (Rp)", xaxis_title="Bulan")
            fig_bulan.update_yaxes(tickprefix="Rp ", tickformat=",.0f")
            st.plotly_chart(fig_bulan, use_container_width=True)
    else:
        st.info("Belum ada data untuk ditampilkan.")

# ----------------------------------------------------------------
# TAB 2: PENDAPATAN
# ----------------------------------------------------------------
with tab2:
    st.subheader("🟩 Data Pendapatan")

    if not df_pendapatan.empty:
        # Filter periode
        col_f1, col_f2, col_f3 = st.columns([1,1,2])
        with col_f1:
            mode = st.selectbox("Filter", ["Semua", "Bulan Ini", "Bulan Lalu", "7 Hari Terakhir", "Custom"], key="filter_p")
        
        hari_ini = date.today()
        if mode == "Bulan Ini":
            tgl_mulai, tgl_selesai = hari_ini.replace(day=1), hari_ini
        elif mode == "Bulan Lalu":
            tgl_selesai = hari_ini.replace(day=1) - pd.Timedelta(days=1)
            tgl_mulai = tgl_selesai.replace(day=1)
        elif mode == "7 Hari Terakhir":
            tgl_mulai, tgl_selesai = hari_ini - pd.Timedelta(days=7), hari_ini
        elif mode == "Custom":
            with col_f2:
                tgl_mulai = st.date_input("Dari", value=df_pendapatan['Tanggal'].min().date(), key="p_dari")
            with col_f3:
                tgl_selesai = st.date_input("Sampai", value=hari_ini, key="p_sampai")
        else:
            tgl_mulai = df_pendapatan['Tanggal'].min().date()
            tgl_selesai = df_pendapatan['Tanggal'].max().date()

        df_p_filtered = df_pendapatan[
            (df_pendapatan['Tanggal'].dt.date >= tgl_mulai) &
            (df_pendapatan['Tanggal'].dt.date <= tgl_selesai)
        ]

        total_p = df_p_filtered['Jumlah'].sum()
        st.markdown(f"""<div style='background:linear-gradient(135deg,#28a745,#20c863);padding:15px 20px;border-radius:10px;color:white;margin-bottom:15px;'>
            <b>Total Pendapatan Periode Ini: Rp {total_p:,.0f}</b> — {len(df_p_filtered)} transaksi
        </div>""", unsafe_allow_html=True)

        kolom_tampil = [c for c in ['Timestamp', 'Kategori', 'Jumlah', 'Catatan'] if c in df_p_filtered.columns]
        df_show = df_p_filtered[kolom_tampil].copy().iloc[::-1].reset_index(drop=True)
        if 'Jumlah' in df_show.columns:
            df_show['Jumlah'] = df_show['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(df_show, use_container_width=True, height=400)
    else:
        st.info("Belum ada data pendapatan. Tambah transaksi dulu.")

# ----------------------------------------------------------------
# TAB 3: PENGELUARAN PER BULAN
# ----------------------------------------------------------------
with tab3:
    st.subheader("🟥 Pengeluaran per Bulan")

    if dict_pengeluaran:
        nama_sheet_list = sorted(dict_pengeluaran.keys())
        bulan_list = [n.replace("Pengeluaran_", "").replace("_", "-") for n in nama_sheet_list]

        # Tabs per bulan
        if len(bulan_list) == 1:
            tabs_bulan = [st.container()]
            bulan_dipilih = [nama_sheet_list[0]]
        else:
            tabs_bulan = st.tabs(bulan_list)
            bulan_dipilih = nama_sheet_list

        for i, (tab_b, nama_sheet) in enumerate(zip(tabs_bulan, bulan_dipilih)):
            with tab_b:
                df_bln = dict_pengeluaran[nama_sheet]
                total_bln = df_bln['Jumlah'].sum() if 'Jumlah' in df_bln.columns else 0
                jumlah_transaksi = len(df_bln)
                rata_rata = total_bln / jumlah_transaksi if jumlah_transaksi > 0 else 0

                # Kartu ringkasan bulan
                cb1, cb2, cb3 = st.columns(3)
                with cb1:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#dc3545,#ff4d5e);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;opacity:0.9;'>TOTAL BULAN INI</p>
                        <h3 style='margin:5px 0 0 0;'>Rp {total_bln:,.0f}</h3>
                    </div>""", unsafe_allow_html=True)
                with cb2:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#6c757d,#495057);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;opacity:0.9;'>JUMLAH TRANSAKSI</p>
                        <h3 style='margin:5px 0 0 0;'>{jumlah_transaksi} transaksi</h3>
                    </div>""", unsafe_allow_html=True)
                with cb3:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#fd7e14,#e65c00);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;opacity:0.9;'>RATA-RATA PER TRANSAKSI</p>
                        <h3 style='margin:5px 0 0 0;'>Rp {rata_rata:,.0f}</h3>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Grafik kategori bulan ini
                if 'Kategori' in df_bln.columns:
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        df_kat = df_bln.groupby('Kategori')['Jumlah'].sum().reset_index().sort_values('Jumlah', ascending=True)
                        fig_kat = px.bar(df_kat, x='Jumlah', y='Kategori', orientation='h',
                            color='Jumlah', color_continuous_scale='Reds', text_auto=True)
                        fig_kat.update_traces(texttemplate='Rp %{x:,.0f}', textposition='outside', textfont_size=9)
                        fig_kat.update_layout(height=280, margin=dict(t=10,b=10),
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            coloraxis_showscale=False, title="Pengeluaran per Kategori")
                        st.plotly_chart(fig_kat, use_container_width=True)
                    with col_g2:
                        fig_pie2 = px.pie(df_kat, values='Jumlah', names='Kategori', hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set3,
                            title="Proporsi Kategori")
                        fig_pie2.update_traces(textposition='inside', textinfo='percent+label')
                        fig_pie2.update_layout(showlegend=False, height=280, margin=dict(t=30,b=10),
                            paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_pie2, use_container_width=True)

                # Tabel detail
                kolom_tampil = [c for c in ['Timestamp', 'Kategori', 'Jumlah', 'Catatan'] if c in df_bln.columns]
                df_show = df_bln[kolom_tampil].copy().iloc[::-1].reset_index(drop=True)
                if 'Jumlah' in df_show.columns:
                    df_show['Jumlah'] = df_show['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
                st.dataframe(df_show, use_container_width=True, height=300)

                # Total di bawah tabel
                st.markdown(f"""<div style='background:#f8d7da;padding:12px 20px;border-radius:8px;border-left:5px solid #dc3545;margin-top:10px;'>
                    <b style='color:#721c24;'>🧮 Total Pengeluaran {bulan_list[i]}: Rp {total_bln:,.0f}</b>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Belum ada data pengeluaran per bulan.")

# ----------------------------------------------------------------
# TAB 4: HAPUS TRANSAKSI
# ----------------------------------------------------------------
with tab4:
    st.subheader("🗑️ Hapus Transaksi")

    service_account_ada = True
    try:
        _ = st.secrets["gcp_service_account"]
    except:
        service_account_ada = False

    if not service_account_ada:
        st.warning("⚠️ Fitur hapus memerlukan Service Account yang aktif.")
    else:
        hapus_dari = st.radio("Hapus dari:", ["Pendapatan", "Pengeluaran (pilih bulan)"], horizontal=True)

        if hapus_dari == "Pendapatan":
            if not df_pendapatan.empty:
                def label_p(row):
                    j = f"Rp {row['Jumlah']:,.0f}" if isinstance(row['Jumlah'], (int,float)) else row['Jumlah']
                    return f"📅 {row.get('Timestamp','')} | {row.get('Kategori','')} | {j}"
                pilihan = {label_p(r): r.get('_baris_sheet', i+2) for i, (_, r) in enumerate(df_pendapatan.iterrows())}
                col1, col2 = st.columns([3,1])
                with col1:
                    dipilih = st.selectbox("Pilih transaksi:", list(pilihan.keys()))
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Hapus", type="primary", use_container_width=True):
                        ok, msg = hapus_baris("Pendapatan", pilihan[dipilih])
                        if ok:
                            st.cache_data.clear()
                            st.success("✅ Berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("Tidak ada data pendapatan.")
        else:
            if dict_pengeluaran:
                nama_sheet_hapus = st.selectbox("Pilih bulan:",
                    sorted(dict_pengeluaran.keys()),
                    format_func=lambda x: x.replace("Pengeluaran_","").replace("_","-"))
                df_hapus = dict_pengeluaran[nama_sheet_hapus]

                def label_e(row):
                    j = f"Rp {row['Jumlah']:,.0f}" if isinstance(row['Jumlah'], (int,float)) else row['Jumlah']
                    cat = row.get('Catatan','')
                    label = f"📅 {row.get('Timestamp','')} | {row.get('Kategori','')} | {j}"
                    if pd.notna(cat) and str(cat).strip():
                        label += f" — {cat}"
                    return label

                pilihan_e = {label_e(r): r.get('_baris_sheet', i+2) for i, (_, r) in enumerate(df_hapus.iterrows())}
                col1, col2 = st.columns([3,1])
                with col1:
                    dipilih_e = st.selectbox("Pilih transaksi:", list(pilihan_e.keys()))
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Hapus", type="primary", use_container_width=True, key="hapus_e"):
                        ok, msg = hapus_baris(nama_sheet_hapus, pilihan_e[dipilih_e])
                        if ok:
                            st.cache_data.clear()
                            st.success("✅ Berhasil dihapus!")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("Tidak ada data pengeluaran.")

# ----------------------------------------------------------------
# TAB 5: PENGATURAN
# ----------------------------------------------------------------
with tab5:
    st.subheader("⚙️ Pengaturan & Migrasi Data")

    st.markdown("### 📦 Migrasi Data Lama")
    st.info("""
    Tombol di bawah akan membaca data dari sheet lama (`Form_Responses` / `Form Responses 1`)
    dan memisahkannya ke sheet baru:
    - **Pendapatan** → sheet `Pendapatan`
    - **Pengeluaran** → sheet `Pengeluaran_YYYY_MM` sesuai bulan
    """)

    if st.button("🚀 Mulai Migrasi Data Sekarang", type="primary"):
        client = get_gsheet_client()
        if not client:
            st.error("❌ Service Account belum aktif. Tidak bisa migrasi.")
        else:
            with st.spinner("Sedang memindahkan data..."):
                ok, msg = pindahkan_data_ke_sheet_baru(client)
                if ok:
                    st.cache_data.clear()
                    st.success("✅ Migrasi berhasil! Refresh halaman.")
                    st.rerun()
                else:
                    st.error(f"❌ Gagal: {msg}")

    st.markdown("---")
    st.markdown("### 🔄 Update Rekap Bulanan")
    st.info("Klik tombol ini untuk memperbarui sheet Rekap dengan total pengeluaran per bulan.")
    if st.button("📊 Update Rekap"):
        with st.spinner("Memperbarui rekap..."):
            update_rekap_bulanan()
        st.success("✅ Rekap diperbarui!")

    st.markdown("---")
    with st.expander("🔐 Cara Ubah Password Login"):
        st.markdown("""
        Di Streamlit Cloud → **Settings → Secrets**, tambahkan:
        ```toml
        [users]
        admin = "hash_sha256_password_anda"
        ```
        Generate hash di: https://emn178.github.io/online-tools/sha256.html

        Default login: `admin` / `dompetku123`
        """)

# =================================================================
# 8. FORM TAMBAH TRANSAKSI (FIXED DI BAWAH)
# =================================================================
st.markdown("---")
st.subheader("➕ Tambah Transaksi Baru")

with st.form("form_keuangan", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        pilihan_jenis = st.selectbox("Jenis Transaksi", ["Pengeluaran", "Pendapatan"])
    with col_b:
        if pilihan_jenis == "Pengeluaran":
            pilihan_kategori = st.selectbox("Kategori", ["Makanan & Minuman","Transportasi","Belanja bulanan","Tagihan & Listrik","Hiburan","Lainnya"])
        else:
            pilihan_kategori = st.selectbox("Kategori", ["Gaji Utama","Bonus / Proyek","Investasi","Pemberian","Lainnya"])
    col_c, col_d = st.columns(2)
    with col_c:
        input_jumlah = st.number_input("Nominal Uang (Rp)", min_value=0, value=0, step=5000)
    with col_d:
        input_catatan = st.text_input("Keterangan (Opsional)", placeholder="misal: Makan siang")
    tombol_simpan = st.form_submit_button("💾 Simpan Transaksi", use_container_width=True)

if tombol_simpan:
    if input_jumlah > 0:
        with st.spinner("Menyimpan..."):
            # Coba via API dulu, fallback ke Google Form
            ok, msg = tambah_transaksi_ke_sheet(pilihan_jenis, pilihan_kategori, input_jumlah, input_catatan)
            if not ok:
                # Fallback Google Form
                try:
                    payload = {
                        "submit": "Submit",
                        "entry.171028022": pilihan_jenis,
                        "entry.1723834692": pilihan_kategori,
                        "entry.674028951": input_jumlah,
                        "entry.1977277942": input_catatan
                    }
                    requests.post(FORM_URL, data=payload, timeout=10)
                    ok = True
                except:
                    ok = False

        if ok:
            st.cache_data.clear()
            st.success("✅ Transaksi berhasil disimpan!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Gagal menyimpan transaksi.")
    else:
        st.error("⚠️ Nominal harus lebih dari Rp 0!")