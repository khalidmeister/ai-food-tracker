import streamlit as st
import requests
import json
import pandas as pd
from PIL import Image
import io
import pillow_heif
import plotly.express as px
import os 
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_TITLE = "Food Tracking Assistant"
WORKSHEET_NAME = "Sheet1"
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")

@st.cache_resource
def init_google_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_TITLE).worksheet(WORKSHEET_NAME)

def load_sheet_data():
    try:
        sheet = init_google_sheet()
        data = sheet.get_all_values() # Ambil mentah biar ga error kalau ada header kosong
        
        if len(data) <= 1:
            return pd.DataFrame()
            
        # Ambil header dan baris isi
        headers = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=headers if len(headers) == len(rows[0]) else None)
        
        # Normalisasi nama kolom sesuai struktur sheet kamu
        df.columns = ["Timestamp", "menu_name", "preparation_tag", "Has Fried", "Has Santan", "raw_json"]
        
        # Conversions & Normalization
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df["is_fried"] = df["Has Fried"].str.upper() == "TRUE"
        df["is_santan"] = df["Has Santan"].str.upper() == "TRUE"
        
        return df
    except Exception as e:
        st.error(f"Error parse sheet: {e}")
        return pd.DataFrame()

tab1, tab2 = st.tabs(["📷 Upload & Analysis", "📊 Weekly Analytics"])

with tab1:
    pillow_heif.register_heif_opener()

    st.set_page_config(page_title="AI Meal Tracker (Polisi Makan)", page_icon="🥗", layout="wide")

    API_URL = st.sidebar.text_input("API Base URL", "http://localhost:8000")

    st.title("🥗 AI Meal Tracker (Food Police)")
    st.caption("Powered by Apple Foundation Model (`fm` CLI) + Local FastAPI & Google Sheets Sync")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📷 Upload Foto Makanan")
        uploaded_file = st.file_uploader("Pilih foto piring makanan (HEIC/JPG/PNG)", type=["jpg", "jpeg", "png", "heic"])
        
        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            image = Image.open(io.BytesIO(bytes_data))

            st.image(uploaded_file, caption="Foto Piring Makanan", width=300)
            
            if st.button("🚨 Analisis Komponen Makanan", type="primary"):
                with st.spinner("Apple Foundation Model sedang membedah bahan..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        res = requests.post(f"{API_URL}/analyze", files=files)
                        
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state["last_analysis"] = data
                            st.success("Analisis Selesai & Data Berhasil Di-log!")
                        else:
                            st.error(f"Error {res.status_code}: {res.text}")
                    except Exception as e:
                        st.error(f"Gagal koneksi ke API: {str(e)}")

    with col2:
        st.subheader("📊 Hasil Deteksi & Polisi Alert")
        if "last_analysis" in st.session_state:
            data = st.session_state["last_analysis"]
            
            st.markdown(f"### Menu: **{data['menu_name']}**")
            st.write(f"**Preparation Tags:** {', '.join(data['preparation_tags'])}")
            
            # Display Warning Status
            if data["has_fried"] or data["has_santan"]:
                st.error(data["warning_message"])
            else:
                st.success(data["warning_message"])
                
            # Display Ingredients Table
            st.markdown("#### Detail Komponen Bahan:")
            df_ing = pd.DataFrame(data["ingredients"])
            st.dataframe(df_ing, use_container_width=True)
        else:
            st.info("Upload foto makanan di sebelah kiri untuk melihat rincian bahan & peringatan kesehatan.")


with tab2:
    st.subheader("📈 Laporan Mingguan Polisi Makan")
    
    df = load_sheet_data()
    
    if not df.empty:
        # Filter 7 Hari Terakhir
        seven_days_ago = pd.Timestamp.now() - pd.Timedelta(days=7)
        df_weekly = df[df["Timestamp"] >= seven_days_ago]
        
        # 1. Summary Cards
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Makan Ter-log", len(df_weekly))
        m2.metric("Total Porsi Gorengan 🍳", int(df_weekly["is_fried"].sum()))
        m3.metric("Total Porsi Santan 🥥", int(df_weekly["is_santan"].sum()))
        
        st.divider()
        
        # 2. Daily Bar Chart
        st.markdown("#### 📊 Distribusi Makanan Berrisiko Harian")
        df_weekly["Date"] = df_weekly["Timestamp"].dt.date
        chart_data = df_weekly.groupby("Date")[["is_fried", "is_santan"]].sum().reset_index()
        
        fig = px.bar(
            chart_data, 
            x="Date", 
            y=["is_fried", "is_santan"],
            title="Frekuensi Gorengan vs Santan Harian",
            labels={"value": "Porsi", "variable": "Jenis Alert"},
            color_discrete_map={"is_fried": "#FF4B4B", "is_santan": "#FFAA00"},
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 3. Clean Table View
        st.markdown("#### 📜 Riwayat Makan (Clean View)")
        st.dataframe(
            df[["Timestamp", "menu_name", "preparation_tag", "Has Fried", "Has Santan"]],
            use_container_width=True
        )
    else:
        st.info("Belum ada data riwayat makanan.")