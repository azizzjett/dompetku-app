import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import plotly.express as px
import plotly.graph_objects as go

# =================================================================
# 1. KONFIGURASI UTAMA & LINK DATABASE
# =================================================================
# Link CSV langsung dari Google Sheets yang sudah di-publish to web
DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vREdDOrXtztLOHd-Km9QDgjjjhzbmMS7J5VYlgknK9Y5Rm47Yf0nHey-Gt3MBiADuUQRtVagLIG1w8h/pub?gid=535445139&single=true&output=csv"

st.set_page_config(page_title="Dompetku Premium", page_icon="💰", layout="wide")

# ---- Custom CSS Styling ----
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 10px;
    }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("💰 Dompetku Realtime Monitoring")
st.caption("Sistem Pelacak Keuangan Mandiri — Terintegrasi Google Sheets")
st.markdown("---")

# =================================================================
# 2. FUNGSI MEMBACA DATA (DENGAN DEBUG INFO)
# =================================================================
@st.cache_data(ttl=10)  # Cache 10 detik saja agar tetap "realtime"
def muat_data():
    try:
        df = pd.read_csv(DATA_URL)

        # Rename kolom Timestamp dari Google Form
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'Tanggal'})

        # Cari kolom jumlah secara fleksibel (case-insensitive)
        kolom_jumlah = [c for c in df.columns if 'jumlah' in c.lower() or 'nominal' in c.lower()]
        if kolom_jumlah:
            df = df.rename(columns={kolom_jumlah[0]: 'Jumlah'})

        # Cari kolom jenis
        kolom_jenis = [c for c in df.columns if 'jenis' in c.lower() or 'tipe' in c.lower()]
        if kolom_jenis:
            df = df.rename(columns={kolom_jenis[0]: 'Jenis'})

        # Cari kolom kategori
        kolom_kategori = [c for c in df.columns if 'kategori' in c.lower() or 'category' in c.lower()]
        if kolom_kategori:
            df = df.rename(columns={kolom_kategori[0]: 'Kategori'})

        # Cari kolom catatan
        kolom_catatan = [c for c in df.columns if 'catatan' in c.lower() or 'keterangan' in c.lower() or 'note' in c.lower()]
        if kolom_catatan:
            df = df.rename(columns={kolom_catatan[0]: 'Catatan'})

        # Parse tanggal
        df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
        df['Tanggal_Display'] = df['Tanggal'].dt.strftime('%Y-%m-%d %H:%M')
        df['Tanggal_Hari'] = df['Tanggal'].dt.strftime('%Y-%m-%d')
        df['Bulan'] = df['Tanggal'].dt.strftime('%Y-%m')

        # Parse jumlah
        if 'Jumlah' in df.columns:
            df['Jumlah'] = pd.to_numeric(df['Jumlah'], errors='coerce').fillna(0)
        else:
            df['Jumlah'] = 0

        return df, None  # (data, error_message)

    except Exception as e:
        return pd.DataFrame(columns=['Tanggal', 'Tanggal_Display', 'Tanggal_Hari', 'Bulan', 'Jenis', 'Kategori', 'Jumlah', 'Catatan']), str(e)


# =================================================================
# 3. LOAD DATA + TAMPILKAN STATUS KONEKSI
# =================================================================
df_keuangan, error_koneksi = muat_data()

# Tombol refresh manual di sidebar
with st.sidebar:
    st.markdown("### ⚙️ Panel Kontrol")
    if st.button("🔄 Refresh Data Sekarang"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("**Status Koneksi**")
    if error_koneksi:
        st.error(f"❌ Gagal: {error_koneksi}")
        st.markdown("""
        **Solusi:**
        1. Buka Google Sheets Anda
        2. Klik **File → Share → Publish to web**
        3. Pilih sheet `Form_Responses`
        4. Klik **Publish**
        """)
    elif df_keuangan.empty:
        st.warning("⚠️ Terhubung, tapi data masih kosong.")
    else:
        st.success(f"✅ Terhubung — {len(df_keuangan)} transaksi")

    st.markdown("---")
    st.caption(f"🕐 Terakhir diperbarui: {datetime.now().strftime('%H:%M:%S')}")


# =================================================================
# 4. TAMPILAN UTAMA — JIKA ADA DATA
# =================================================================
if not df_keuangan.empty and 'Jenis' in df_keuangan.columns:

    total_pendapatan = df_keuangan[df_keuangan['Jenis'] == 'Pendapatan']['Jumlah'].sum()
    total_pengeluaran = df_keuangan[df_keuangan['Jenis'] == 'Pengeluaran']['Jumlah'].sum()
    sisa_saldo = total_pendapatan - total_pengeluaran
    rasio_hemat = (sisa_saldo / total_pendapatan * 100) if total_pendapatan > 0 else 0

    # ---- KARTU RINGKASAN SALDO ----
    st.subheader("📊 Ringkasan Saldo Anda")
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#28a745,#20c863); padding:20px; border-radius:12px; color:white;'>
            <p style='margin:0; font-size:13px; opacity:0.9;'>🟩 TOTAL PENDAPATAN</p>
            <h2 style='margin:5px 0 0 0; font-size:24px;'>Rp {total_pendapatan:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#dc3545,#ff4d5e); padding:20px; border-radius:12px; color:white;'>
            <p style='margin:0; font-size:13px; opacity:0.9;'>🟥 TOTAL PENGELUARAN</p>
            <h2 style='margin:5px 0 0 0; font-size:24px;'>Rp {total_pengeluaran:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        warna = "linear-gradient(135deg,#007bff,#0056b3)" if sisa_saldo >= 0 else "linear-gradient(135deg,#fd7e14,#e65c00)"
        st.markdown(f"""
        <div style='background:{warna}; padding:20px; border-radius:12px; color:white;'>
            <p style='margin:0; font-size:13px; opacity:0.9;'>🧮 SISA SALDO BERSIH</p>
            <h2 style='margin:5px 0 0 0; font-size:24px;'>Rp {sisa_saldo:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        warna_rasio = "linear-gradient(135deg,#6f42c1,#5a2d8a)" if rasio_hemat >= 20 else "linear-gradient(135deg,#ffc107,#e0a800)"
        st.markdown(f"""
        <div style='background:{warna_rasio}; padding:20px; border-radius:12px; color:white;'>
            <p style='margin:0; font-size:13px; opacity:0.9;'>💡 RASIO TABUNGAN</p>
            <h2 style='margin:5px 0 0 0; font-size:24px;'>{rasio_hemat:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- GRAFIK BARIS 1: Tren + Pie ----
    st.subheader("📈 Analisis Grafik Keuangan")
    g1, g2 = st.columns([2, 1])

    with g1:
        st.markdown("**📅 Tren Pendapatan vs Pengeluaran per Hari**")

        # Aggregate per hari
        df_tren = df_keuangan.groupby(['Tanggal_Hari', 'Jenis'])['Jumlah'].sum().reset_index()
        df_tren = df_tren.pivot(index='Tanggal_Hari', columns='Jenis', values='Jumlah').fillna(0).reset_index()

        if 'Pendapatan' not in df_tren.columns:
            df_tren['Pendapatan'] = 0
        if 'Pengeluaran' not in df_tren.columns:
            df_tren['Pengeluaran'] = 0

        df_tren = df_tren.sort_values('Tanggal_Hari')

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_tren['Tanggal_Hari'], y=df_tren['Pendapatan'],
            mode='lines+markers', name='Pendapatan',
            line=dict(color='#28a745', width=3),
            marker=dict(size=8),
            fill='tozeroy', fillcolor='rgba(40,167,69,0.1)'
        ))
        fig_line.add_trace(go.Scatter(
            x=df_tren['Tanggal_Hari'], y=df_tren['Pengeluaran'],
            mode='lines+markers', name='Pengeluaran',
            line=dict(color='#dc3545', width=3),
            marker=dict(size=8),
            fill='tozeroy', fillcolor='rgba(220,53,69,0.1)'
        ))
        fig_line.update_layout(
            xaxis_title="Tanggal",
            yaxis_title="Jumlah (Rp)",
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
            height=320,
            margin=dict(t=20, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        fig_line.update_yaxes(tickprefix="Rp ", tickformat=",.0f")
        st.plotly_chart(fig_line, use_container_width=True)

    with g2:
        st.markdown("**🍩 Alokasi Pengeluaran**")
        df_pengeluaran = df_keuangan[df_keuangan['Jenis'] == 'Pengeluaran']
        if not df_pengeluaran.empty and 'Kategori' in df_pengeluaran.columns:
            df_pie = df_pengeluaran.groupby('Kategori')['Jumlah'].sum().reset_index()
            fig_pie = px.pie(
                df_pie, values='Jumlah', names='Kategori', hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                showlegend=False, height=320,
                margin=dict(t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Belum ada data pengeluaran.")

    # ---- GRAFIK BARIS 2: Bar Bulanan + Bar Kategori ----
    g3, g4 = st.columns(2)

    with g3:
        st.markdown("**📊 Perbandingan Bulanan**")
        df_bulanan = df_keuangan.groupby(['Bulan', 'Jenis'])['Jumlah'].sum().reset_index()
        fig_bar_bulan = px.bar(
            df_bulanan, x='Bulan', y='Jumlah', color='Jenis', barmode='group',
            color_discrete_map={'Pendapatan': '#28a745', 'Pengeluaran': '#dc3545'},
            text_auto=True
        )
        fig_bar_bulan.update_traces(texttemplate='Rp %{y:,.0f}', textposition='outside', textfont_size=9)
        fig_bar_bulan.update_layout(
            height=300, margin=dict(t=20, b=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            yaxis_title="Jumlah (Rp)", xaxis_title="Bulan",
            legend=dict(orientation="h", y=1.1)
        )
        fig_bar_bulan.update_yaxes(tickprefix="Rp ", tickformat=",.0f")
        st.plotly_chart(fig_bar_bulan, use_container_width=True)

    with g4:
        st.markdown("**📋 Top Kategori Pengeluaran**")
        if not df_pengeluaran.empty and 'Kategori' in df_pengeluaran.columns:
            df_top_kat = df_pengeluaran.groupby('Kategori')['Jumlah'].sum().reset_index().sort_values('Jumlah', ascending=True)
            fig_hbar = px.bar(
                df_top_kat, x='Jumlah', y='Kategori', orientation='h',
                color='Jumlah', color_continuous_scale='Reds',
                text_auto=True
            )
            fig_hbar.update_traces(texttemplate='Rp %{x:,.0f}', textposition='outside', textfont_size=9)
            fig_hbar.update_layout(
                height=300, margin=dict(t=20, b=20),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Jumlah (Rp)", yaxis_title="",
                coloraxis_showscale=False
            )
            fig_hbar.update_xaxes(tickprefix="Rp ", tickformat=",.0f")
            st.plotly_chart(fig_hbar, use_container_width=True)
        else:
            st.info("Belum ada data pengeluaran.")

    st.markdown("---")

    # ---- LIVE DATABASE TABLE ----
    st.subheader("📜 Live Database (Google Sheets)")

    # Filter interaktif
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_jenis = st.multiselect("Filter Jenis", options=df_keuangan['Jenis'].unique().tolist(), default=df_keuangan['Jenis'].unique().tolist())
    with col_filter2:
        if 'Kategori' in df_keuangan.columns:
            filter_kat = st.multiselect("Filter Kategori", options=df_keuangan['Kategori'].dropna().unique().tolist(), default=df_keuangan['Kategori'].dropna().unique().tolist())
        else:
            filter_kat = []

    df_filtered = df_keuangan[df_keuangan['Jenis'].isin(filter_jenis)]
    if filter_kat and 'Kategori' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Kategori'].isin(filter_kat)]

    # Pilih kolom yang ditampilkan
    kolom_tampil = [c for c in ['Tanggal_Display', 'Jenis', 'Kategori', 'Jumlah', 'Catatan'] if c in df_filtered.columns]
    df_tampil = df_filtered[kolom_tampil].rename(columns={'Tanggal_Display': 'Tanggal'}).iloc[::-1]

    df_tampil_display = df_tampil.copy()
    if 'Jumlah' in df_tampil_display.columns:
        df_tampil_display['Jumlah'] = df_tampil_display['Jumlah'].apply(lambda x: f"Rp {x:,.0f}" if isinstance(x, (int, float)) else x)
    st.dataframe(df_tampil_display, use_container_width=True, height=350)
    st.caption(f"Menampilkan {len(df_tampil)} dari {len(df_keuangan)} transaksi")

else:
    # Pesan jika data kosong atau gagal koneksi
    st.warning("⚠️ Tidak ada data yang berhasil dibaca.")
    st.info("""
    **Kemungkinan penyebab:**
    - Google Sheets belum di-publish ke publik
    - Nama tab bukan `Form_Responses`  
    - Koneksi internet terganggu

    **Cara publish Google Sheets:**
    1. Buka spreadsheet Anda
    2. **File → Share → Publish to web**
    3. Pilih sheet `Form_Responses` → Format `CSV`
    4. Klik **Publish** → konfirmasi OK
    """)

st.markdown("---")

# =================================================================
# 5. FORM INPUT TRANSAKSI BARU
# =================================================================
st.subheader("➕ Tambah Transaksi Baru")

with st.form("form_keuangan", clear_on_submit=True):
    col_a, col_b = st.columns(2)

    with col_a:
        pilihan_jenis = st.selectbox("Jenis Transaksi", ["Pengeluaran", "Pendapatan"])

    with col_b:
        if pilihan_jenis == "Pengeluaran":
            pilihan_kategori = st.selectbox("Kategori", ["Makanan & Minuman", "Transportasi", "Belanja bulanan", "Tagihan & Listrik", "Hiburan", "Lainnya"])
        else:
            pilihan_kategori = st.selectbox("Kategori", ["Gaji Utama", "Bonus / Proyek", "Investasi", "Pemberian", "Lainnya"])

    col_c, col_d = st.columns(2)
    with col_c:
        input_jumlah = st.number_input("Nominal Uang (Rp)", min_value=0, value=0, step=5000)
    with col_d:
        input_catatan = st.text_input("Keterangan (Opsional)", placeholder="misal: Beli baju baru")

    tombol_simpan = st.form_submit_button("💾 Simpan & Sinkronisasi", use_container_width=True)

if tombol_simpan:
    if input_jumlah > 0:
        with st.spinner("Sedang menyinkronkan ke database cloud..."):
            try:
                form_url = "https://docs.google.com/forms/d/e/1FAIpQLSeRTFqYWhRkGMwvBvUqsgz7RWfQUw36JuLuPjcdnGnu09-9ug/formResponse"

                payload = {
                    "submit": "Submit",
                    "entry.171028022": pilihan_jenis,
                    "entry.1723834692": pilihan_kategori,
                    "entry.674028951": input_jumlah,
                    "entry.1977277942": input_catatan
                }

                resp = requests.post(form_url, data=payload, timeout=10)
                st.cache_data.clear()  # Hapus cache agar data baru langsung muncul
                st.success("✅ Tersimpan dan Sinkron Berhasil!")
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"❌ Gagal mengirim. Error: {e}")
    else:
        st.error("⚠️ Nominal uang harus lebih besar dari Rp 0!")