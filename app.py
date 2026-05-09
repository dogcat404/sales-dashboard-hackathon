import streamlit as st
import pandas as pd
import plotly.express as px
from itertools import combinations
from collections import Counter

st.set_page_config(
    page_title="Sales Intelligence Dashboard",
    page_icon="📊",
    layout="wide"
)

@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_excel("data_penjualan.xlsx")

    # Konversi tanggal serial Excel menjadi tanggal normal
    df["tanggal"] = pd.to_datetime(df["tgl_transaksi"], unit="D", origin="1899-12-30")

    # Fitur tambahan
    df["bulan"] = df["tanggal"].dt.to_period("M").astype(str)
    df["nama_hari"] = df["tanggal"].dt.day_name()
    df["tanggal_str"] = df["tanggal"].dt.strftime("%Y-%m-%d")

    return df

st.title("📊 Sales Intelligence Dashboard")
st.caption("Dashboard visualisasi data penjualan untuk hackathon berbasis Python dan Streamlit.")

st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload file Excel data_penjualan.xlsx",
    type=["xlsx"]
)

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error("Data belum ditemukan. Upload file Excel melalui sidebar atau simpan data_penjualan.xlsx di repository GitHub.")
    st.stop()

# Filter tanggal
min_date = df["tanggal"].min().date()
max_date = df["tanggal"].max().date()

date_range = st.sidebar.date_input(
    "Pilih rentang tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df["tanggal"].dt.date >= start_date) & (df["tanggal"].dt.date <= end_date)]

# KPI transaksi
trx = df.groupby("nomor_struk").agg(
    basket_value=("total_nilai", "sum"),
    item_unik=("kode_produk", "nunique"),
    total_qty=("jumlah_terjual", "sum")
).reset_index()

total_revenue = df["total_nilai"].sum()
total_qty = df["jumlah_terjual"].sum()
jumlah_transaksi = df["nomor_struk"].nunique()
jumlah_produk = df["kode_produk"].nunique()
aov = trx["basket_value"].mean() if len(trx) else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Revenue", f"Rp{total_revenue:,.0f}".replace(",", "."))
col2.metric("Total Qty", f"{total_qty:,.0f}".replace(",", "."))
col3.metric("Transaksi", f"{jumlah_transaksi:,.0f}".replace(",", "."))
col4.metric("Produk Unik", f"{jumlah_produk:,.0f}".replace(",", "."))
col5.metric("AOV", f"Rp{aov:,.0f}".replace(",", "."))

st.divider()

# Agregasi produk
top_produk = df.groupby(["kode_produk", "nama_produk"], as_index=False).agg(
    revenue=("total_nilai", "sum"),
    qty=("jumlah_terjual", "sum"),
    transaksi=("nomor_struk", "nunique"),
    harga_rata2=("harga", "mean")
).sort_values("revenue", ascending=False)

# Agregasi harian
daily = df.groupby("tanggal", as_index=False).agg(
    revenue=("total_nilai", "sum"),
    qty=("jumlah_terjual", "sum"),
    transaksi=("nomor_struk", "nunique")
)

tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Produk",
    "Pareto & Matrix",
    "Market Basket"
])

with tab1:
    st.subheader("Tren Revenue Harian")
    fig_daily = px.line(
        daily,
        x="tanggal",
        y="revenue",
        markers=True,
        title="Tren Revenue Harian"
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Revenue per Hari")
        weekday = df.groupby("nama_hari", as_index=False).agg(
            revenue=("total_nilai", "sum"),
            transaksi=("nomor_struk", "nunique")
        )
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday["nama_hari"] = pd.Categorical(weekday["nama_hari"], categories=order, ordered=True)
        weekday = weekday.sort_values("nama_hari")

        fig_weekday = px.bar(
            weekday,
            x="nama_hari",
            y="revenue",
            title="Revenue Berdasarkan Hari"
        )
        st.plotly_chart(fig_weekday, use_container_width=True)

    with col_b:
        st.subheader("Distribusi Nilai Transaksi")
        fig_hist = px.histogram(
            trx,
            x="basket_value",
            nbins=30,
            title="Distribusi Basket Value"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    st.subheader("Top Produk Berdasarkan Revenue")

    top_n = st.slider("Jumlah produk yang ditampilkan", 5, 30, 15)

    fig_top = px.bar(
        top_produk.head(top_n).sort_values("revenue"),
        x="revenue",
        y="nama_produk",
        orientation="h",
        title=f"Top {top_n} Produk Berdasarkan Revenue",
        hover_data=["qty", "transaksi", "harga_rata2"]
    )
    st.plotly_chart(fig_top, use_container_width=True)

    st.subheader("Tabel Ringkasan Produk")
    st.dataframe(top_produk, use_container_width=True)

with tab3:
    st.subheader("Pareto Product Intelligence")

    pareto = top_produk.copy()
    pareto["cum_revenue_pct"] = pareto["revenue"].cumsum() / pareto["revenue"].sum() * 100

    fig_pareto = px.bar(
        pareto.head(25),
        x="nama_produk",
        y="revenue",
        title="Pareto Produk Berdasarkan Revenue",
        hover_data=["cum_revenue_pct", "qty"]
    )
    fig_pareto.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.subheader("Product Role Matrix")
    fig_matrix = px.scatter(
        top_produk,
        x="qty",
        y="revenue",
        size="transaksi",
        hover_name="nama_produk",
        hover_data=["harga_rata2"],
        title="Product Role Matrix: Quantity vs Revenue"
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

    st.info(
        "Interpretasi: produk di kanan berarti volume tinggi, produk di atas berarti revenue tinggi, "
        "dan bubble besar berarti sering muncul dalam transaksi."
    )

with tab4:
    st.subheader("Market Basket Analysis")

    basket = df.groupby("nomor_struk")["nama_produk"].apply(lambda x: sorted(set(x)))

    pair_counter = Counter()
    for items in basket:
        for pair in combinations(items, 2):
            pair_counter[pair] += 1

    pairs = pd.DataFrame([
        {"produk_a": a, "produk_b": b, "frekuensi": c}
        for (a, b), c in pair_counter.items()
    ]).sort_values("frekuensi", ascending=False)

    if len(pairs) == 0:
        st.warning("Tidak ada pasangan produk yang dapat dihitung.")
    else:
        top_pairs = pairs.head(20).copy()
        top_pairs["pasangan_produk"] = top_pairs["produk_a"] + " + " + top_pairs["produk_b"]

        fig_pairs = px.bar(
            top_pairs.sort_values("frekuensi"),
            x="frekuensi",
            y="pasangan_produk",
            orientation="h",
            title="Top 20 Produk yang Sering Dibeli Bersama"
        )
        st.plotly_chart(fig_pairs, use_container_width=True)

        st.subheader("Rekomendasi Bundling")
        best_pair = pairs.iloc[0]
        st.success(
            f"Bundling paling potensial: {best_pair['produk_a']} + {best_pair['produk_b']} "
            f"karena muncul bersama sebanyak {best_pair['frekuensi']} kali."
        )

        st.dataframe(pairs.head(50), use_container_width=True)

st.divider()
st.subheader("Kesimpulan Otomatis")

if len(top_produk) > 0:
    best_product = top_produk.iloc[0]
    st.write(
        f"Produk dengan kontribusi revenue tertinggi adalah **{best_product['nama_produk']}** "
        f"dengan total revenue **Rp{best_product['revenue']:,.0f}** dan quantity terjual "
        f"**{best_product['qty']:,.0f} unit**."
        .replace(",", ".")
    )

if len(daily) > 0:
    best_day = daily.sort_values("revenue", ascending=False).iloc[0]
    st.write(
        f"Hari dengan revenue tertinggi adalah **{best_day['tanggal'].date()}** "
        f"dengan total revenue **Rp{best_day['revenue']:,.0f}**."
        .replace(",", ".")
    )