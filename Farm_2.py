import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil

# ---------- Configuration ----------
st.set_page_config(page_title="Farm Bin & Delivery Tracker", page_icon="🌾", layout="wide")

DATA_DIR = os.path.dirname(__file__) if "__file__" in globals() else "."
BIN_CSV = os.path.join(DATA_DIR, "bin_setup.csv")
DELIVERIES_CSV = os.path.join(DATA_DIR, "deliveries.csv")
UNLOADS_CSV = os.path.join(DATA_DIR, "unloads.csv")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# ---------- Helpers ----------
def _init_csv(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def backup_file(path):
    if os.path.exists(path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"{os.path.basename(path)}.{ts}.bak")
        shutil.copy2(path, backup_path)
        return backup_path
    return None

def load_bin_setup():
    _init_csv(BIN_CSV, ["Bin", "Capacity_bu", "Variety", "Bushels_in_bin"])
    df = pd.read_csv(BIN_CSV)
    if "Bushels_in_bin" not in df.columns:
        df["Bushels_in_bin"] = 0.0
    df["Bushels_in_bin"] = df["Bushels_in_bin"].fillna(0.0)
    return df

def save_bin_setup(df):
    df.to_csv(BIN_CSV, index=False)

def load_deliveries():
    _init_csv(DELIVERIES_CSV, ["Timestamp", "Truck", "Bin", "Variety", "Bushels", "Notes"])
    return pd.read_csv(DELIVERIES_CSV)

def save_deliveries(df):
    df.to_csv(DELIVERIES_CSV, index=False)

def load_unloads():
    _init_csv(UNLOADS_CSV, ["Timestamp", "Bin", "Variety", "Bushels", "Destination", "Notes"])
    return pd.read_csv(UNLOADS_CSV)

def save_unloads(df):
    df.to_csv(UNLOADS_CSV, index=False)

# ---------- Initialize CSVs ----------
_init_csv(BIN_CSV, ["Bin", "Capacity_bu", "Variety", "Bushels_in_bin"])
_init_csv(DELIVERIES_CSV, ["Timestamp", "Truck", "Bin", "Variety", "Bushels", "Notes"])
_init_csv(UNLOADS_CSV, ["Timestamp", "Bin", "Variety", "Bushels", "Destination", "Notes"])

# ---------- Load Data ----------
bin_setup = load_bin_setup()
deliveries = load_deliveries()
unloads = load_unloads()

# ---------- UI ----------
st.title("🌾 Farm Bin & Delivery Tracker")
st.caption("Track deliveries and unloads, prevent variety mixing.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown(f"Data files: bin_setup.csv, deliveries.csv, unloads.csv")
    if st.button("Reload Data"):
        st.cache_data.clear()
        st.rerun()
    with st.expander("Reset / Clear Tables"):
        if st.button("Clear Deliveries"):
            if st.checkbox("✅ Confirm clear deliveries", key="confirm_deliveries"):
                backup_path = backup_file(DELIVERIES_CSV)
                pd.DataFrame(columns=deliveries.columns).to_csv(DELIVERIES_CSV, index=False)
                st.success(f"Deliveries cleared (backup saved: {backup_path})")

        if st.button("Clear Unloads"):
            if st.checkbox("✅ Confirm clear unloads", key="confirm_unloads"):
                backup_path = backup_file(UNLOADS_CSV)
                pd.DataFrame(columns=unloads.columns).to_csv(UNLOADS_CSV, index=False)
                st.success(f"Unloads cleared (backup saved: {backup_path})")

        if st.button("Reset Bins to 0"):
            if st.checkbox("✅ Confirm reset bins", key="confirm_bins"):
                backup_path = backup_file(BIN_CSV)
                bin_setup["Bushels_in_bin"] = 0.0
                save_bin_setup(bin_setup)
                st.success(f"Bins reset to 0 bushels (backup saved: {backup_path})")

# Tabs
tab_dashboard, tab_bins, tab_deliveries, tab_unloads, tab_records = st.tabs(
    ["📊 Dashboard", "🧺 Bins Setup", "🚚 Add Delivery", "⬇️ Unload Bin", "📜 Records"]
)

# ---------- Dashboard ----------
with tab_dashboard:
    st.subheader("Farm Totals & Varieties")
    if bin_setup.empty:
        st.info("No bins yet.")
    else:
        total_capacity = bin_setup["Capacity_bu"].sum()
        total_in_bins = bin_setup["Bushels_in_bin"].sum()
        st.metric("Total Capacity (bu)", total_capacity)
        st.metric("Total Grain in Bins (bu)", total_in_bins)

        st.markdown("### Grain by Variety")
        variety_totals = bin_setup.groupby("Variety")["Bushels_in_bin"].sum().reset_index()
        variety_totals = variety_totals[variety_totals["Variety"] != ""]
        if variety_totals.empty:
            st.info("No grain in bins yet.")
        else:
            for _, row in variety_totals.iterrows():
                st.metric(row["Variety"], row["Bushels_in_bin"])

# ---------- Bins Setup ----------
with tab_bins:
    st.subheader("Bins Setup (1–35)")
    default_bins = [f"Bin {i}" for i in range(1, 36)]
    for b in default_bins:
        if b not in bin_setup["Bin"].tolist():
            bin_setup = pd.concat([bin_setup, pd.DataFrame([{"Bin": b, "Capacity_bu": 0.0, "Variety": "", "Bushels_in_bin": 0.0}])], ignore_index=True)
    save_bin_setup(bin_setup)

    edited = st.data_editor(
        bin_setup[["Bin", "Capacity_bu", "Variety"]],
        num_rows="dynamic",
        use_container_width=True
    )
    if st.button("Save Bins Setup"):
        for idx, row in edited.iterrows():
            bin_setup.loc[bin_setup["Bin"] == row["Bin"], ["Capacity_bu", "Variety"]] = row[["Capacity_bu", "Variety"]]
        save_bin_setup(bin_setup)
        st.success("Bins updated")

# ---------- Add Delivery ----------
with tab_deliveries:
    st.subheader("Log Delivery")
    if bin_setup.empty:
        st.info("Add bins first")
    else:
        with st.form("delivery_form", clear_on_submit=True):
            truck = st.text_input("Truck / Ticket")
            bin_choice = st.selectbox("Select Bin", bin_setup["Bin"].tolist())
            variety = st.text_input("Variety")
            bushels = st.number_input("Bushels Delivered", min_value=0.0, step=10.0)
            notes = st.text_input("Notes")
            submit_delivery = st.form_submit_button("Add Delivery")
        if submit_delivery:
            idx = bin_setup.index[bin_setup["Bin"] == bin_choice][0]
            current_var = bin_setup.at[idx, "Variety"] or ""
            if current_var and variety.strip() != current_var:
                st.error(f"Can't mix {variety.strip()} with {current_var}")
            else:
                bin_setup.at[idx, "Bushels_in_bin"] += bushels
                if not current_var:
                    bin_setup.at[idx, "Variety"] = variety.strip()
                save_bin_setup(bin_setup)
                deliveries = pd.concat([deliveries, pd.DataFrame([{"Timestamp": now_ts(), "Truck": truck, "Bin": bin_choice, "Variety": variety.strip(), "Bushels": bushels, "Notes": notes}])], ignore_index=True)
                save_deliveries(deliveries)
                st.success(f"Added {bushels} bu to {bin_choice}")

# ---------- Unload Bin ----------
with tab_unloads:
    st.subheader("Unload from Bin")
    if bin_setup.empty:
        st.info("Add bins first")
    else:
        with st.form("unload_form", clear_on_submit=True):
            bin_choice = st.selectbox("Select Bin", bin_setup["Bin"].tolist(), key="unload_bin")
            destination = st.text_input("Destination")
            bushels = st.number_input("Bushels to unload", min_value=0.0, step=10.0)
            notes = st.text_input("Notes")
            submit_unload = st.form_submit_button("Unload")
        if submit_unload:
            idx = bin_setup.index[bin_setup["Bin"] == bin_choice][0]
            available = bin_setup.at[idx, "Bushels_in_bin"]
            take = min(bushels, available)
            bin_setup.at[idx, "Bushels_in_bin"] -= take
            save_bin_setup(bin_setup)
            unloads = pd.concat([unloads, pd.DataFrame([{"Timestamp": now_ts(), "Bin": bin_choice, "Variety": bin_setup.at[idx, "Variety"], "Bushels": take, "Destination": destination, "Notes": notes}])], ignore_index=True)
            save_unloads(unloads)
            st.success(f"Unloaded {take} bu from {bin_choice}")

# ---------- Records ----------
with tab_records:
    st.subheader("Deliveries & Unloads")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Deliveries**")
        st.dataframe(deliveries.sort_values("Timestamp", ascending=False))
    with col2:
        st.markdown("**Unloads**")
        st.dataframe(unloads.sort_values("Timestamp", ascending=False))

