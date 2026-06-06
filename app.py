import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# 1. ATUR TAMPILAN MOBILE
st.set_page_config(page_title="Dompetku Alternatif", page_icon="💰", layout="centered")
st.title("💰 Dompetku GSheets")
st.caption("Versi Simpel Tanpa File Credentials JSON")
st.markdown("---")

# 2. INISIALISASI KONEKSI GSHEETS
# Streamlit akan otomatis membaca URL dari file .streamlit/secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. FUNGSI MEMBACA DATA
@st.cache_data(ttl=5) # Refresh data otomatis tiap 5 detik
def muat_data():
    try:
        # Membaca data dari Sheet1
        df = conn.read(worksheet="Sheet1", ttl="5s")
        # Membersihkan baris yang benar-benar kosong jika ada
        df = df.dropna(subset=['Tanggal', 'Jenis', 'Jumlah'])
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.date
        df['Jumlah'] = pd.to_numeric(df['Jumlah'])
        return df
    except:
        return pd.DataFrame(columns=['Tanggal', 'Jenis', 'Kategori', 'Jumlah', 'Catatan'])

df_keuangan = muat_data()

# 4. DASHBOARD RINGKASAN SALDO
st.subheader("📊 Ringkasan Saldo")
if not df_keuangan.empty:
    total_pendapatan = df_keuangan[df_keuangan['Jenis'] == 'Pendapatan']['Jumlah'].sum()
    total_pengeluaran = df_keuangan[df_keuangan['Jenis'] == 'Pengeluaran']['Jumlah'].sum()
    sisa_saldo = total_pendapatan - total_pengeluaran

    k1, k2, k3 = st.columns(3)
    k1.metric("Pemasukan", f"Rp {total_pendapatan:,.0f}")
    k2.metric("Pengeluaran", f"Rp {total_pengeluaran:,.0f}")
    k3.metric("Sisa Saldo", f"Rp {sisa_saldo:,.0f}")
else:
    st.info("Belum ada data transaksi di Google Sheets.")
st.markdown("---")

# 5. FORM INPUT TRANSAKSI BARU (LANGSUNG MASUK)
st.subheader("➕ Tambah Transaksi Baru")
with st.form("form_keuangan", clear_on_submit=True):
    pilihan_tanggal = st.date_input("Tanggal Transaksi", datetime.now().date())
    pilihan_jenis = st.selectbox("Jenis Transaksi", ["Pengeluaran", "Pendapatan"])
    
    if pilihan_jenis == "Pengeluaran":
        pilihan_kategori = st.selectbox("Kategori", ["Makanan & Minuman", "Transportasi", "Belanja bulanan", "Tagihan & Listrik", "Hiburan", "Lainnya"])
    else:
        pilihan_kategori = st.selectbox("Kategori", ["Gaji Utama", "Bonus / Proyek", "Investasi", "Pemberian", "Lainnya"])
        
    input_jumlah = st.number_input("Nominal Uang (Rp)", min_value=0, value=0, step=5000)
    input_catatan = st.text_input("Catatan / Keterangan (Opsional)", placeholder="misal: Beli nasi goreng")
    
    tombol_simpan = st.form_submit_button("Simpan Otomatis")

if tombol_simpan:
    if input_jumlah > 0:
        with st.spinner("Menyimpan ke Google Sheets..."):
            try:
                # 1. Siapkan data baru dalam bentuk DataFrame
                data_baru = pd.DataFrame([{
                    "Tanggal": pilihan_tanggal.strftime("%Y-%m-%d"),
                    "Jenis": pilihan_jenis,
                    "Kategori": pilihan_kategori,
                    "Jumlah": input_jumlah,
                    "Catatan": input_catatan
                }])
                
                # 2. Gabungkan data lama dengan data baru
                df_diperbarui = pd.concat([df_keuangan, data_baru], ignore_index=True)
                
                # 3. Tulis ulang ke Google Sheets secara instan
                conn.update(worksheet="Sheet1", data=df_diperbarui)
                
                st.success("Berhasil disimpan otomatis!")
                st.balloons()
                
                # Clear cache agar langsung memuat data terbaru
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan data. Pastikan setelan share sudah 'Editor'. Error: {e}")
    else:
        st.error("Gagal menyimpan! Jumlah uang harus lebih besar dari Rp 0.")

st.markdown("---")

# 6. RIWAYAT TRANSAKSI TERAKHIR
st.subheader("📜 5 Transaksi Terakhir")
if not df_keuangan.empty:
    st.dataframe(df_keuangan.tail(5), use_container_width=True)
else:
    st.write("Riwayat transaksi masih kosong.")
st.markdown("---")

# 7. VISUALISASI GRAFIK LINGKARAN
st.subheader("🍩 Analisis Pengeluaran")
if not df_keuangan.empty:
    df_pengeluaran = df_keuangan[df_keuangan['Jenis'] == 'Pengeluaran']
    if not df_pengeluaran.empty:
        df_group = df_pengeluaran.groupby('Kategori')['Jumlah'].sum().reset_index()
        fig_pie = px.pie(df_group, values='Jumlah', names='Kategori', hole=0.4)
        fig_pie.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Belum ada data pengeluaran untuk dianalisis.")