import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ---------- Configuration ----------
st.set_page_config(page_title="Poplar Wood Farms - Farm Tracker", page_icon="🌾", layout="wide")

DATA_DIR = os.path.dirname(__file__) if "__file__" in globals() else "."
BIN_CSV = os.path.join(DATA_DIR, "bin_setup.csv")
DELIVERIES_CSV = os.path.join(DATA_DIR, "deliveries.csv")
UNLOADS_CSV = os.path.join(DATA_DIR, "unloads.csv")

# ---------- Helpers ----------
def _init_csv(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def percent(x, total):
    try:
        return max(0.0, min(100.0, 100.0 * float(x)/float(total)))
    except:
        return 0.0

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

# ---------- Clear old bins and pre-fill 31 bins if empty ----------
if bin_setup.empty:
    bins_default = [{"Bin": f"Bin {i}", "Capacity_bu": 0.0, "Variety": "", "Bushels_in_bin": 0.0} for i in range(1, 32)]
    bin_setup = pd.DataFrame(bins_default)
    save_bin_setup(bin_setup)

# ---------- UI ----------
st.title("🌾 Poplar Wood Farms - Farm Bin & Delivery Tracker")
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
            pd.DataFrame(columns=deliveries.columns).to_csv(DELIVERIES_CSV, index=False)
            st.success("Deliveries cleared")
        if st.button("Clear Unloads"):
            pd.DataFrame(columns=unloads.columns).to_csv(UNLOADS_CSV, index=False)
            st.success("Unloads cleared")
        if st.button("Reset Bins to 0"):
            bin_setup["Bushels_in_bin"] = 0.0
            save_bin_setup(bin_setup)
            st.success("Bins reset to 0 bushels")

# ---------- Tabs ----------
tab_dashboard, tab_bin_status, tab_deliveries, tab_unloads, tab_records, tab_bins = st.tabs(
    ["📊 Dashboard", "🧺 Bin Status", "🚚 Add Delivery", "⬇️ Unload Bin", "📜 Records", "📝 Bin Setup"]
)

# ---------- Dashboard ----------
with tab_dashboard:
    st.subheader("Farm Totals & Varieties")
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

# ---------- Bin Status ----------
with tab_bin_status:
    st.subheader("Current Bin Status")
    if bin_setup.empty:
        st.info("No bins yet.")
    else:
        display_df = bin_setup.copy()
        display_df["Remaining"] = display_df["Capacity_bu"] - display_df["Bushels_in_bin"]
        display_df = display_df[["Bin", "Variety", "Capacity_bu", "Bushels_in_bin", "Remaining"]]
        display_df.rename(columns={
            "Capacity_bu": "Capacity (bu)",
            "Bushels_in_bin": "In Bin (bu)",
            "Remaining": "Remaining (bu)"
        }, inplace=True)
        st.dataframe(display_df.style.format({
            "Capacity (bu)": "{:.0f}",
            "In Bin (bu)": "{:.0f}",
            "Remaining (bu)": "{:.0f}"
        }))

# ---------- Add Delivery ----------
with tab_deliveries:
    st.subheader("Log Delivery")
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

# ---------- Bin Setup ----------
with tab_bins:
    st.subheader("Add / Edit Bin")
    bins_list = bin_setup["Bin"].tolist()
    selected_bin = st.selectbox("Select Bin to Edit or Add New", ["New Bin"] + bins_list)

    if selected_bin == "New Bin":
        bin_name = st.text_input("Bin Name")
        capacity = st.number_input("Capacity (bushels)", min_value=0.0, step=100.0)
        variety = st.text_input("Variety")
        if st.button("Add Bin"):
            if not bin_name.strip():
                st.error("Enter bin name")
            elif bin_name in bin_setup["Bin"].values:
                st.error("Bin already exists")
            else:
                bin_setup = pd.concat([bin_setup, pd.DataFrame([{"Bin": bin_name, "Capacity_bu": capacity, "Variety": variety.strip(), "Bushels_in_bin": 0.0}])], ignore_index=True)
                save_bin_setup(bin_setup)
                st.success(f"{bin_name} added")
    else:
        idx = bin_setup.index[bin_setup["Bin"] == selected_bin][0]
        new_capacity = st.number_input("Capacity (bushels)", value=bin_setup.at[idx, "Capacity_bu"], min_value=0.0, step=100.0)
        new_variety = st.text_input("Variety", value=bin_setup.at[idx, "Variety"])
        if st.button("Update Bin"):
            bin_setup.at[idx, "Capacity_bu"] = new_capacity
            bin_setup.at[idx, "Variety"] = new_variety.strip()
            save_bin_setup(bin_setup)
            st.success(f"{selected_bin} updated")
