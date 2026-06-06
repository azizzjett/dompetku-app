import streamlit as st
import pandas as pd
from datetime import datetime
import requests 
import plotly.express as px

# =================================================================
# 1. KONFIGURASI UTAMA & DATABASE
# =================================================================
# ID Spreadsheet Anda (Membaca data dari Google Sheets Anda yang di-share publik)
SPREADSHEET_ID = "1LoC_moM3dZDhLzhy7dfbWKZVq5fuplWjMEh-9IEUQE8" 
DATA_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=0"

st.set_page_config(page_title="Dompetku Mandiri", page_icon="💰", layout="centered")
st.title("💰 Dompetku Pro V2")
st.caption("Aplikasi Keuangan Online - Bebas Error Keamanan")
st.markdown("---")

# =================================================================
# 2. FUNGSI UNTUK MEMBACA DATA
# =================================================================
@st.cache_data(ttl=5) 
def muat_data():
    try:
        df = pd.read_csv(DATA_URL)
        # Jika kolom pertama Google Sheets berubah menjadi 'Timestamp' karena Form, kita sesuaikan
        if 'Timestamp' in df.columns:
            df = df.rename(columns={'Timestamp': 'Tanggal'})
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.date
        df['Jumlah'] = pd.to_numeric(df['Jumlah'])
        return df
    except:
        return pd.DataFrame(columns=['Tanggal', 'Jenis', 'Kategori', 'Jumlah', 'Catatan'])

df_keuangan = muat_data()

# =================================================================
# 3. DASHBOARD RINGKASAN SALDO
# =================================================================
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
    st.info("Belum ada data transaksi terdeteksi di Google Sheets.")
st.markdown("---")

# =================================================================
# 4. FORM INPUT TRANSAKSI BARU
# =================================================================
st.subheader("➕ Tambah Transaksi Baru")
with st.form("form_keuangan", clear_on_submit=True):
    pilihan_jenis = st.selectbox("Jenis Transaksi", ["Pengeluaran", "Pendapatan"])
    
    if pilihan_jenis == "Pengeluaran":
        pilihan_kategori = st.selectbox("Kategori", ["Makanan & Minuman", "Transportasi", "Belanja bulanan", "Tagihan & Listrik", "Hiburan", "Lainnya"])
    else:
        pilihan_kategori = st.selectbox("Kategori", ["Gaji Utama", "Bonus / Proyek", "Investasi", "Pemberian", "Lainnya"])
        
    input_jumlah = st.number_input("Nominal Uang (Rp)", min_value=0, value=0, step=5000)
    input_catatan = st.text_input("Keterangan Tambahan (Opsional)", placeholder="misal: Beli nasi goreng")
    
    tombol_simpan = st.form_submit_button("Simpan Otomatis")

# Logika simpan otomatis mengirim ke Google Form Anda
if tombol_simpan:
    if input_jumlah > 0:
        with st.spinner("Sedang menyimpan data ke cloud..."):
            try:
                # Menggunakan Link Google Form Anda yang sudah diubah ke formResponse
                form_url = "https://docs.google.com/forms/d/e/1FAIpQLSeRTFqYWhRkGMwvBvUqsgz7RWfQUw36JuLuPjcdnGnu09-9ug/formResponse"
                
                # Payload otomatis menggunakan teks nama pertanyaan sebagai kunci akses
                payload = {
                    "submit": "Submit",
                    "Jenis": pilihan_jenis,
                    "Kategori": pilihan_kategori,
                    "Jumlah": input_jumlah,
                    "Catatan": input_catatan
                }
                
                # Menembak data secara tersembunyi ke Google Form
                requests.post(form_url, data=payload)
                
                st.success("Berhasil disimpan otomatis!")
                st.balloons()
                
                # Clear cache agar data terbaru langsung ditarik ke layar aplikasi
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan data. Error: {e}")
    else:
        st.error("Gagal menyimpan! Jumlah uang harus lebih besar dari Rp 0.")

st.markdown("---")

# =================================================================
# 5. RIWAYAT TRANSAKSI TERAKHIR
# =================================================================
st.subheader("📜 5 Transaksi Terakhir")
if not df_keuangan.empty:
    st.dataframe(df_keuangan.tail(5), use_container_width=True)
else:
    st.write("Riwayat transaksi masih kosong.")
st.markdown("---")

# =================================================================
# 6. VISUALISASI GRAFIK LINGKARAN
# =================================================================
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