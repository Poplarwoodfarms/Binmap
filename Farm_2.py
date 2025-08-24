import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ---------- File Paths ----------
BIN_CSV = "bins.csv"
DELIVERIES_CSV = "deliveries.csv"
UNLOADS_CSV = "unloads.csv"
BACKUP_DIR = "backups"

# ---------- Initialize Files ----------
def init_file(filename, columns):
    if not os.path.exists(filename):
        pd.DataFrame(columns=columns).to_csv(filename, index=False)

init_file(BIN_CSV, ["Bin", "Capacity_bu", "Variety", "Bushels_in_bin"])
init_file(DELIVERIES_CSV, ["Date", "Truck", "Field", "Bushels", "Variety", "Bin"])
init_file(UNLOADS_CSV, ["Date", "Bin", "Bushels_unloaded"])

# ---------- One-time session backup ----------
if "backup_done" not in st.session_state:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Clear old backups
    for f in os.listdir(BACKUP_DIR):
        os.remove(os.path.join(BACKUP_DIR, f))

    # Make one fresh backup
    for fname in [BIN_CSV, DELIVERIES_CSV, UNLOADS_CSV]:
        if os.path.exists(fname):
            backup_path = os.path.join(BACKUP_DIR, f"{os.path.basename(fname)}_{timestamp}.bak.csv")
            pd.read_csv(fname).to_csv(backup_path, index=False)

    st.session_state["backup_done"] = True

# ---------- Load/Save Helpers ----------
def load_csv(filename):
    return pd.read_csv(filename)

def save_csv(df, filename):
    df.to_csv(filename, index=False)

# ---------- Data ----------
bin_setup = load_csv(BIN_CSV)
deliveries = load_csv(DELIVERIES_CSV)
unloads = load_csv(UNLOADS_CSV)

# ---------- Streamlit Tabs ----------
st.title("🌾 Farm Bin & Delivery Tracker")

tab_deliveries, tab_unloads, tab_records, tab_bins = st.tabs(
    ["Deliveries", "Unload", "Records", "Bin Setup"]
)

# ---------- Deliveries ----------
with tab_deliveries:
    st.subheader("Add Delivery")
    date = st.date_input("Date")
    truck = st.text_input("Truck")
    field = st.text_input("Field")
    bushels = st.number_input("Bushels", min_value=0.0, step=1.0)
    variety = st.text_input("Variety")
    bin_choice = st.selectbox("Select Bin", bin_setup["Bin"].tolist())

    if st.button("Add Delivery"):
        new_row = {
            "Date": date,
            "Truck": truck,
            "Field": field,
            "Bushels": bushels,
            "Variety": variety,
            "Bin": bin_choice
        }
        deliveries = pd.concat([deliveries, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(deliveries, DELIVERIES_CSV)
        bin_setup.loc[bin_setup["Bin"] == bin_choice, "Bushels_in_bin"] += bushels
        save_csv(bin_setup, BIN_CSV)
        st.success("Delivery added")

# ---------- Unloads ----------
with tab_unloads:
    st.subheader("Unload Grain")
    date = st.date_input("Unload Date")
    bin_choice = st.selectbox("Select Bin", bin_setup["Bin"].tolist())
    bushels_unloaded = st.number_input("Bushels Unloaded", min_value=0.0, step=1.0)

    if st.button("Unload"):
        new_row = {
            "Date": date,
            "Bin": bin_choice,
            "Bushels_unloaded": bushels_unloaded
        }
        unloads = pd.concat([unloads, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(unloads, UNLOADS_CSV)
        bin_setup.loc[bin_setup["Bin"] == bin_choice, "Bushels_in_bin"] -= bushels_unloaded
        save_csv(bin_setup, BIN_CSV)
        st.success("Unload recorded")

# ---------- Records ----------
with tab_records:
    st.subheader("All Deliveries")
    st.dataframe(deliveries)

    st.subheader("All Unloads")
    st.dataframe(unloads)

    st.subheader("Bin Status")
    st.dataframe(bin_setup)

# ---------- Bin Setup ----------
with tab_bins:
    st.subheader("Bins Setup (1–35)")
    default_bins = [f"Bin {i}" for i in range(1, 36)]
    for b in default_bins:
        if b not in bin_setup["Bin"].tolist():
            bin_setup = pd.concat([bin_setup, pd.DataFrame([{
                "Bin": b,
                "Capacity_bu": 0.0,
                "Variety": "",
                "Bushels_in_bin": 0.0
            }])], ignore_index=True)
    save_csv(bin_setup, BIN_CSV)

    edited = st.data_editor(
        bin_setup[["Bin", "Capacity_bu", "Variety"]],
        num_rows="dynamic",
        use_container_width=True
    )
    if st.button("Save Bins Setup"):
        for idx, row in edited.iterrows():
            bin_setup.loc[bin_setup["Bin"] == row["Bin"], ["Capacity_bu", "Variety"]] = row[["Capacity_bu", "Variety"]]
        save_csv(bin_setup, BIN_CSV)
        st.success("Bins updated")
