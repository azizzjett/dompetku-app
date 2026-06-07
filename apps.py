import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# =================================================================
# 1. KONFIGURASI UTAMA
# =================================================================
SPREADSHEET_ID = "1yFdjwqVBc5Eu-axzeUHWYwZXmUuTYgGlQza1crm6TiQ"

st.set_page_config(page_title="Dompetku Premium", page_icon="💰", layout="wide")
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 8px 20px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# =================================================================
# 2. LOGIN
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
# 3. GOOGLE API
# =================================================================
def get_creds():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)

def get_gsheet_client():
    try:
        return gspread.authorize(get_creds())
    except Exception as e:
        return None

def get_spreadsheet():
    client = get_gsheet_client()
    if not client:
        return None
    return client.open_by_key(SPREADSHEET_ID)

def get_or_create_sheet(spreadsheet, nama_sheet, header):
    try:
        return spreadsheet.worksheet(nama_sheet)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=nama_sheet, rows=1000, cols=10)
        sheet.append_row(header)
        return sheet

def tambah_transaksi(jenis, kategori, jumlah, catatan, link_struk=""):
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False, "Service account belum dikonfigurasi"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if jenis == "Pendapatan":
            nama_sheet = "Pendapatan"
            header = ["Timestamp", "Kategori", "Jumlah", "Catatan", "Link_Struk"]
        else:
            nama_sheet = f"Pengeluaran_{datetime.now().strftime('%Y_%m')}"
            header = ["Timestamp", "Kategori", "Jumlah", "Catatan", "Link_Struk"]
        sheet = get_or_create_sheet(spreadsheet, nama_sheet, header)
        sheet.append_row([timestamp, kategori, float(jumlah), catatan, link_struk])
        return True, nama_sheet
    except Exception as e:
        return False, str(e)

def hapus_baris(nama_sheet, nomor_baris):
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False, "Service account belum dikonfigurasi"
        sheet = spreadsheet.worksheet(nama_sheet)
        sheet.delete_rows(nomor_baris)
        return True, "Berhasil"
    except Exception as e:
        return False, str(e)

def get_or_create_drive_folder(drive_service, folder_name, parent_id=None):
    """Cari atau buat folder di Google Drive."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    body = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        body['parents'] = [parent_id]
    folder = drive_service.files().create(body=body, fields='id').execute()
    drive_service.permissions().create(
        fileId=folder['id'], body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    return folder['id']

def upload_struk(file_bytes, mime_type, jenis, kategori, catatan):
    """Upload foto struk ke folder per bulan dengan nama file otomatis."""
    try:
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)

        # Buat nama file otomatis: tanggal_kategori_keterangan
        now = datetime.now()
        tanggal_str = now.strftime('%Y-%m-%d')
        bulan_str = now.strftime('%Y-%m')
        catatan_bersih = catatan.strip().replace('/', '-').replace('\\', '-') if catatan else "tanpa-keterangan"
        kategori_bersih = kategori.replace('/', '-').replace('&', 'dan')
        ext = "jpg" if "jpeg" in mime_type else "png"
        nama_file = f"{tanggal_str}_{kategori_bersih}_{catatan_bersih}.{ext}"

        # Struktur folder: Struk_Belanja_Dompetku / 2026-06
        root_id = get_or_create_drive_folder(drive_service, "Struk_Belanja_Dompetku")
        bulan_id = get_or_create_drive_folder(drive_service, bulan_str, parent_id=root_id)

        # Upload file ke folder bulan
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
        file = drive_service.files().create(
            body={'name': nama_file, 'parents': [bulan_id]},
            media_body=media, fields='id, webViewLink'
        ).execute()
        drive_service.permissions().create(
            fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        return True, file['webViewLink'], nama_file
    except Exception as e:
        return False, str(e), ""

# =================================================================
# 4. BACA DATA
# =================================================================
@st.cache_data(ttl=15)
def muat_data():
    hasil = {"pendapatan": pd.DataFrame(), "pengeluaran": {}, "sumber": "ok"}
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        semua_sheet = [s.title for s in spreadsheet.worksheets()]

        if "Pendapatan" in semua_sheet:
            records = spreadsheet.worksheet("Pendapatan").get_all_records()
            if records:
                df = pd.DataFrame(records)
                df['Tanggal'] = pd.to_datetime(df.get('Timestamp', pd.Series(dtype=str)), errors='coerce')
                df['Jumlah'] = pd.to_numeric(df.get('Jumlah', 0), errors='coerce').fillna(0)
                df['_baris_sheet'] = range(2, len(df) + 2)
                hasil["pendapatan"] = df

        for nama in sorted([s for s in semua_sheet if s.startswith("Pengeluaran_")]):
            records = spreadsheet.worksheet(nama).get_all_records()
            if records:
                df = pd.DataFrame(records)
                df['Tanggal'] = pd.to_datetime(df.get('Timestamp', pd.Series(dtype=str)), errors='coerce')
                df['Jumlah'] = pd.to_numeric(df.get('Jumlah', 0), errors='coerce').fillna(0)
                df['_baris_sheet'] = range(2, len(df) + 2)
                df['_nama_sheet'] = nama
                hasil["pengeluaran"][nama] = df

        return hasil, None
    except Exception as e:
        hasil["sumber"] = "error"
        return hasil, str(e)

# =================================================================
# 5. SIDEBAR
# =================================================================
st.title("💰 Dompetku Realtime Monitoring")
st.caption("Sistem Pelacak Keuangan Pribadi — Terintegrasi Google Sheets")
st.markdown("---")

data, error_load = muat_data()
df_pendapatan = data["pendapatan"]
dict_pengeluaran = data["pengeluaran"]
df_pengeluaran_all = pd.concat(dict_pengeluaran.values(), ignore_index=True) if dict_pengeluaran else pd.DataFrame()

with st.sidebar:
    st.markdown(f"### 👤 Halo, {st.session_state.get('username', 'User')}!")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown("**Status**")
    if error_load:
        st.error(f"❌ {error_load}")
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
# 6. RINGKASAN SALDO
# =================================================================
total_pendapatan = df_pendapatan['Jumlah'].sum() if not df_pendapatan.empty else 0
total_pengeluaran = df_pengeluaran_all['Jumlah'].sum() if not df_pengeluaran_all.empty else 0
sisa_saldo = total_pendapatan - total_pengeluaran
rasio_hemat = (sisa_saldo / total_pendapatan * 100) if total_pendapatan > 0 else 0

st.subheader("📊 Ringkasan Saldo")
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
# 7. TABS
# =================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Dashboard", "🟩 Pendapatan", "🟥 Pengeluaran per Bulan", "🗑️ Hapus", "⚙️ Pengaturan"
])

# TAB 1: DASHBOARD
with tab1:
    st.subheader("📈 Grafik Keuangan")
    if not df_pengeluaran_all.empty or not df_pendapatan.empty:
        g1, g2 = st.columns([2, 1])
        with g1:
            st.markdown("**Tren Pendapatan vs Pengeluaran**")
            rows = []
            if not df_pendapatan.empty:
                for _, r in df_pendapatan.iterrows():
                    rows.append({'Tanggal': r['Tanggal'], 'Jumlah': r['Jumlah'], 'Jenis': 'Pendapatan'})
            if not df_pengeluaran_all.empty:
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

        st.markdown("**📊 Total Pengeluaran per Bulan**")
        if dict_pengeluaran:
            rekap_list = [{'Bulan': n.replace("Pengeluaran_","").replace("_","-"),
                'Total': df['Jumlah'].sum()} for n, df in dict_pengeluaran.items()]
            df_rc = pd.DataFrame(rekap_list).sort_values('Bulan')
            fig_b = px.bar(df_rc, x='Bulan', y='Total', color_discrete_sequence=['#dc3545'], text_auto=True)
            fig_b.update_traces(texttemplate='Rp %{y:,.0f}', textposition='outside', textfont_size=10)
            fig_b.update_layout(height=300, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=30,b=20), yaxis_title="Total (Rp)", xaxis_title="Bulan")
            fig_b.update_yaxes(tickprefix="Rp ", tickformat=",.0f")
            st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("Belum ada data untuk ditampilkan.")

# TAB 2: PENDAPATAN
with tab2:
    st.subheader("🟩 Data Pendapatan")
    if not df_pendapatan.empty:
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

        df_pf = df_pendapatan[(df_pendapatan['Tanggal'].dt.date >= tgl_mulai) &
            (df_pendapatan['Tanggal'].dt.date <= tgl_selesai)]
        total_p = df_pf['Jumlah'].sum()
        st.markdown(f"""<div style='background:linear-gradient(135deg,#28a745,#20c863);padding:15px 20px;border-radius:10px;color:white;margin-bottom:15px;'>
            <b>Total Pendapatan: Rp {total_p:,.0f}</b> — {len(df_pf)} transaksi
        </div>""", unsafe_allow_html=True)
        kolom_tampil = [c for c in ['Timestamp','Kategori','Jumlah','Catatan','Link_Struk'] if c in df_pf.columns]
        df_show = df_pf[kolom_tampil].copy().iloc[::-1].reset_index(drop=True)
        if 'Jumlah' in df_show.columns:
            df_show['Jumlah'] = df_show['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(df_show, use_container_width=True, height=400)
    else:
        st.info("Belum ada data pendapatan.")

# TAB 3: PENGELUARAN PER BULAN
with tab3:
    st.subheader("🟥 Pengeluaran per Bulan")
    if dict_pengeluaran:
        nama_sheet_list = sorted(dict_pengeluaran.keys())
        bulan_list = [n.replace("Pengeluaran_","").replace("_","-") for n in nama_sheet_list]
        tabs_bulan = [st.container()] if len(bulan_list) == 1 else st.tabs(bulan_list)
        for i, (tab_b, nama_sheet) in enumerate(zip(tabs_bulan, nama_sheet_list)):
            with tab_b:
                df_bln = dict_pengeluaran[nama_sheet]
                total_bln = df_bln['Jumlah'].sum()
                jml_trx = len(df_bln)
                rata = total_bln / jml_trx if jml_trx > 0 else 0
                cb1, cb2, cb3 = st.columns(3)
                with cb1:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#dc3545,#ff4d5e);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;'>TOTAL BULAN INI</p><h3 style='margin:5px 0 0 0;'>Rp {total_bln:,.0f}</h3></div>""", unsafe_allow_html=True)
                with cb2:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#6c757d,#495057);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;'>JUMLAH TRANSAKSI</p><h3 style='margin:5px 0 0 0;'>{jml_trx} transaksi</h3></div>""", unsafe_allow_html=True)
                with cb3:
                    st.markdown(f"""<div style='background:linear-gradient(135deg,#fd7e14,#e65c00);padding:15px;border-radius:10px;color:white;'>
                        <p style='margin:0;font-size:12px;'>RATA-RATA</p><h3 style='margin:5px 0 0 0;'>Rp {rata:,.0f}</h3></div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if 'Kategori' in df_bln.columns:
                    cg1, cg2 = st.columns(2)
                    with cg1:
                        df_kat = df_bln.groupby('Kategori')['Jumlah'].sum().reset_index().sort_values('Jumlah', ascending=True)
                        fig_kat = px.bar(df_kat, x='Jumlah', y='Kategori', orientation='h',
                            color='Jumlah', color_continuous_scale='Reds', text_auto=True, title="Per Kategori")
                        fig_kat.update_traces(texttemplate='Rp %{x:,.0f}', textposition='outside', textfont_size=9)
                        fig_kat.update_layout(height=280, margin=dict(t=30,b=10),
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
                        st.plotly_chart(fig_kat, use_container_width=True)
                    with cg2:
                        fig_p2 = px.pie(df_kat, values='Jumlah', names='Kategori', hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set3, title="Proporsi")
                        fig_p2.update_traces(textposition='inside', textinfo='percent+label')
                        fig_p2.update_layout(showlegend=False, height=280, margin=dict(t=30,b=10), paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_p2, use_container_width=True)
                kolom_tampil = [c for c in ['Timestamp','Kategori','Jumlah','Catatan','Link_Struk'] if c in df_bln.columns]
                df_show = df_bln[kolom_tampil].copy().iloc[::-1].reset_index(drop=True)
                if 'Jumlah' in df_show.columns:
                    df_show['Jumlah'] = df_show['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
                st.dataframe(df_show, use_container_width=True, height=300)
                st.markdown(f"""<div style='background:#f8d7da;padding:12px 20px;border-radius:8px;border-left:5px solid #dc3545;margin-top:10px;'>
                    <b style='color:#721c24;'>🧮 Total {bulan_list[i]}: Rp {total_bln:,.0f}</b></div>""", unsafe_allow_html=True)
    else:
        st.info("Belum ada data pengeluaran.")

# TAB 4: HAPUS
with tab4:
    st.subheader("🗑️ Hapus Transaksi")
    service_account_ada = True
    try:
        _ = st.secrets["gcp_service_account"]
    except:
        service_account_ada = False

    if not service_account_ada:
        st.warning("⚠️ Fitur hapus memerlukan Service Account aktif.")
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
                nama_sheet_hapus = st.selectbox("Pilih bulan:", sorted(dict_pengeluaran.keys()),
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

# TAB 5: PENGATURAN
with tab5:
    st.subheader("⚙️ Pengaturan")
    with st.expander("🔐 Cara Ubah Password Login"):
        st.markdown("""
        Di Streamlit Cloud → **Settings → Secrets**, tambahkan:
        ```toml
        [users]
        admin = "hash_sha256_password_anda"
        ```
        Generate hash di: https://emn178.github.io/online-tools/sha256.html
        Default: `admin` / `dompetku123`
        """)

# =================================================================
# 8. TAMBAH TRANSAKSI
# =================================================================
st.markdown("---")
st.subheader("➕ Tambah Transaksi Baru")

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

# Kamera toggle
aktifkan_kamera = st.toggle("📷 Aktifkan Kamera Struk")
foto_struk = None
if aktifkan_kamera:
    foto_struk = st.camera_input("Arahkan kamera ke struk belanja")
    if foto_struk:
        st.success("✅ Foto siap disimpan!")

tombol_simpan = st.button("💾 Simpan Transaksi", use_container_width=True, type="primary")

if tombol_simpan:
    if input_jumlah > 0:
        with st.spinner("Menyimpan..."):
            link_struk = ""
            nama_file_struk = ""
            if foto_struk is not None:
                mime = "image/png"
                ok_foto, hasil_foto, nama_file_struk = upload_struk(
                    foto_struk.getvalue(), mime,
                    pilihan_jenis, pilihan_kategori, input_catatan
                )
                if ok_foto:
                    link_struk = hasil_foto
                    st.success(f"📷 Foto tersimpan: `{nama_file_struk}`")
                else:
                    st.warning(f"⚠️ Foto gagal diupload: {hasil_foto}")
            ok, pesan = tambah_transaksi(pilihan_jenis, pilihan_kategori, input_jumlah, input_catatan, link_struk)
        if ok:
            st.cache_data.clear()
            st.success(f"✅ Tersimpan ke sheet {pesan}!")
            if link_struk:
                st.markdown(f"📷 [Lihat Foto Struk]({link_struk})")
            st.balloons()
            st.rerun()
        else:
            st.error(f"❌ Gagal: {pesan}")
    else:
        st.error("⚠️ Nominal harus lebih dari Rp 0!")
