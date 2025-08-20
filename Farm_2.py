import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Farm Bin & Delivery Tracker", page_icon="🌾", layout="wide")

DATA_DIR = os.path.dirname(__file__) if "__file__" in globals() else "."
BIN_CSV = os.path.join(DATA_DIR, "bin_setup.csv")
DELIVERIES_CSV = os.path.join(DATA_DIR, "deliveries.csv")
UNLOADS_CSV = os.path.join(DATA_DIR, "unloads.csv")

# ---------- Helpers ----------
def _init_csv(path: str, columns: list):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)

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

def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def percent(x, total):
    try:
        total = float(total)
        x = float(x)
        if total <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * x / total))
    except Exception:
        return 0.0

# Ensure files exist
_init_csv(BIN_CSV, ["Bin", "Capacity_bu", "Variety", "Bushels_in_bin"])
_init_csv(DELIVERIES_CSV, ["Timestamp", "Truck", "Bin", "Variety", "Bushels", "Notes"])
_init_csv(UNLOADS_CSV, ["Timestamp", "Bin", "Variety", "Bushels", "Destination", "Notes"])

# ---------- Load data ----------
bin_setup = load_bin_setup()
deliveries = load_deliveries()
unloads = load_unloads()

# ---------- UI Header ----------
st.title("🌾 Farm Bin & Delivery Tracker")
st.caption("Add deliveries to bins, prevent variety mixing, and track unloading from bins.")

# ---------- Sidebar: Global Actions ----------
with st.sidebar:
    st.header("⚙️ Settings & Utilities")
    st.markdown("Data files are saved next to this app:")
    st.code(f"bin_setup.csv\n{os.path.basename(DELIVERIES_CSV)}\n{os.path.basename(UNLOADS_CSV)}", language="")

    if st.button("🔄 Reload Data from Disk"):
        st.cache_data.clear()
        st.rerun()

    with st.expander("🧹 Reset / Clear Tables"):
        colr1, colr2, colr3 = st.columns(3)
        with colr1:
            if st.button("Clear Deliveries"):
                pd.DataFrame(columns=["Timestamp", "Truck", "Bin", "Variety", "Bushels", "Notes"]).to_csv(DELIVERIES_CSV, index=False)
                st.success("Deliveries cleared.")
        with colr2:
            if st.button("Clear Unloads"):
                pd.DataFrame(columns=["Timestamp", "Bin", "Variety", "Bushels", "Destination", "Notes"]).to_csv(UNLOADS_CSV, index=False)
                st.success("Unloads cleared.")
        with colr3:
            if st.button("Reset Bin Fill to 0"):
                bs = load_bin_setup()
                if not bs.empty:
                    bs["Bushels_in_bin"] = 0.0
                    save_bin_setup(bs)
                    st.success("All bins set to 0 bushels.")

# ---------- Tabs ----------
tab_dashboard, tab_bins, tab_deliveries, tab_unloads, tab_records = st.tabs(
    ["📊 Dashboard", "🧺 Bins Setup", "🚚 Add Delivery", "⬇️ Unload Bin", "📜 Records"]
)

# ---------- Dashboard ----------
with tab_dashboard:
    st.subheader("Bin Status")
    if bin_setup.empty:
        st.info("No bins yet. Add bins in the **Bins Setup** tab.")
    else:
        # Calculate remaining and percent
        view = bin_setup.copy()
        view["Remaining_bu"] = (view["Capacity_bu"].fillna(0) - view["Bushels_in_bin"].fillna(0)).clip(lower=0)
        view["% Full"] = [percent(x, t) for x, t in zip(view["Bushels_in_bin"], view["Capacity_bu"])]

        # Progress bars
        for _, row in view.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['Bin']}** — Variety: `{row['Variety'] if pd.notna(row['Variety']) and row['Variety'] != '' else '—'}`")
                st.write(f"Capacity: {row['Capacity_bu']} bu | In Bin: {row['Bushels_in_bin']} bu | Remaining: {row['Remaining_bu']} bu")
                st.progress(float(row["% Full"]) / 100.0 if row["% Full"] else 0.0, text=f"{row['% Full']:.1f}% full")

        st.markdown("—")
        totals = view.agg({"Capacity_bu": "sum", "Bushels_in_bin": "sum", "Remaining_bu": "sum"})
        st.metric("Total Capacity (bu)", f"{totals['Capacity_bu']:.0f}")
        st.metric("Total In Bins (bu)", f"{totals['Bushels_in_bin']:.0f}")
        st.metric("Total Remaining (bu)", f"{totals['Remaining_bu']:.0f}")

# ---------- Bins Setup ----------
with tab_bins:
    st.subheader("Add / Edit Bins")
    with st.form("add_bin_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2,1,1])
        bin_name = col1.text_input("Bin Name/Number", placeholder="e.g., Bin 1")
        capacity = col2.number_input("Capacity (bushels)", min_value=0.0, step=100.0)
        variety = col3.text_input("Assigned Variety (optional)", placeholder="e.g., CWRS")
        submitted = st.form_submit_button("Add / Update Bin")

    if submitted:
        if not bin_name.strip():
            st.error("Please enter a bin name.")
        else:
            # Add or update
            idx = None
            if "Bin" in bin_setup.columns:
                matches = bin_setup.index[bin_setup["Bin"].astype(str) == bin_name]
                if len(matches) > 0:
                    idx = matches[0]

            if idx is not None:
                # Update existing
                if capacity is not None and capacity >= 0:
                    bin_setup.at[idx, "Capacity_bu"] = float(capacity)
                if variety is not None:
                    bin_setup.at[idx, "Variety"] = variety.strip()
                if "Bushels_in_bin" not in bin_setup.columns:
                    bin_setup["Bushels_in_bin"] = 0.0
                save_bin_setup(bin_setup)
                st.success(f"Updated {bin_name}.")
            else:
                # Create new
                new_row = {
                    "Bin": bin_name.strip(),
                    "Capacity_bu": float(capacity) if capacity else 0.0,
                    "Variety": variety.strip(),
                    "Bushels_in_bin": 0.0
                }
                bin_setup = pd.concat([bin_setup, pd.DataFrame([new_row])], ignore_index=True)
                save_bin_setup(bin_setup)
                st.success(f"Added {bin_name}.")

    if not bin_setup.empty:
        st.markdown("### Current Bins")
        st.dataframe(bin_setup, use_container_width=True, hide_index=True)

        with st.expander("Edit / Remove Bins"):
            bins = bin_setup["Bin"].tolist()
            sel = st.selectbox("Choose Bin to Edit/Remove", options=bins)
            if sel:
                idx = bin_setup.index[bin_setup["Bin"] == sel][0]
                colb1, colb2, colb3, colb4 = st.columns([2,1,1,1])
                new_name = colb1.text_input("Bin Name", bin_setup.at[idx, "Bin"], key="edit_name")
                new_cap = colb2.number_input("Capacity (bu)", value=float(bin_setup.at[idx, "Capacity_bu"]), step=100.0, key="edit_cap")
                new_var = colb3.text_input("Variety", value=str(bin_setup.at[idx, "Variety"] or ""), key="edit_var")
                reset_fill = colb4.checkbox("Reset fill to 0", value=False, key="edit_reset")

                colb5, colb6 = st.columns(2)
                if colb5.button("Save Changes"):
                    bin_setup.at[idx, "Bin"] = new_name.strip()
                    bin_setup.at[idx, "Capacity_bu"] = float(new_cap)
                    bin_setup.at[idx, "Variety"] = new_var.strip()
                    if reset_fill:
                        bin_setup.at[idx, "Bushels_in_bin"] = 0.0
                    save_bin_setup(bin_setup)
                    st.success("Changes saved.")
                if colb6.button("Delete Bin", type="primary"):
                    bin_setup = bin_setup.drop(index=idx).reset_index(drop=True)
                    save_bin_setup(bin_setup)
                    st.warning("Bin deleted.")

# ---------- Add Delivery (Add to Bin) ----------
with tab_deliveries:
    st.subheader("Log Delivery")
    if bin_setup.empty:
        st.info("Add a bin first.")
    else:
        col1, col2 = st.columns([1,1])
        with st.form("delivery_form", clear_on_submit=True):
            truck = st.text_input("Truck / Ticket #", placeholder="e.g., Truck 12 or Ticket 34567")
            bin_choice = st.selectbox("Select Bin", options=bin_setup["Bin"].tolist())
            variety = st.text_input("Variety", placeholder="e.g., CWRS")
            bushels = st.number_input("Bushels Delivered", min_value=0.0, step=10.0)
            notes = st.text_input("Notes (optional)")
            submit_delivery = st.form_submit_button("Add Delivery")

        if submit_delivery:
            if not bin_choice or bushels <= 0:
                st.error("Please select a bin and enter bushels > 0.")
            else:
                idx = bin_setup.index[bin_setup["Bin"] == bin_choice][0]
                # Variety logic
                current_var = str(bin_setup.at[idx, "Variety"] or "").strip()
                if current_var == "":
                    # Set variety to this delivery's variety on first fill
                    bin_setup.at[idx, "Variety"] = variety.strip()
                    current_var = variety.strip()

                if variety.strip() != current_var:
                    st.error(f"⚠️ {bin_choice} already has '{current_var}'. Can't mix with '{variety.strip()}'.")
                else:
                    # Capacity check
                    cap = float(bin_setup.at[idx, "Capacity_bu"] or 0.0)
                    current = float(bin_setup.at[idx, "Bushels_in_bin"] or 0.0)
                    remaining = max(0.0, cap - current) if cap > 0 else None

                    if cap > 0 and bushels > remaining:
                        st.warning(f"Adding would exceed capacity by {bushels - remaining:.1f} bu. Adding only {remaining:.1f} bu.")
                        add_amt = remaining
                    else:
                        add_amt = bushels

                    # Update bin
                    bin_setup.at[idx, "Bushels_in_bin"] = current + add_amt
                    save_bin_setup(bin_setup)

                    # Record delivery (full requested amount for record, plus stored 'Added_to_bin')
                    new_row = {
                        "Timestamp": now_ts(),
                        "Truck": truck.strip(),
                        "Bin": bin_choice,
                        "Variety": current_var,
                        "Bushels": float(bushels),
                        "Notes": notes.strip()
                    }
                    deliveries = pd.concat([deliveries, pd.DataFrame([new_row])], ignore_index=True)
                    save_deliveries(deliveries)

                    st.success(f"Added {add_amt:.1f} bu to {bin_choice}. In bin: {bin_setup.at[idx, 'Bushels_in_bin']:.1f} bu.")

# ---------- Unload (Subtract from Bin) ----------
with tab_unloads:
    st.subheader("Unload from Bin")
    if bin_setup.empty:
        st.info("Add a bin first.")
    else:
        with st.form("unload_form", clear_on_submit=True):
            bin_choice_u = st.selectbox("Select Bin", options=bin_setup["Bin"].tolist(), key="unload_bin")
            destination = st.text_input("Destination (elevator, truck, field, etc.)", placeholder="e.g., GrainCo Elevator")
            bushels_u = st.number_input("Bushels to Unload", min_value=0.0, step=10.0, key="unload_bu")
            notes_u = st.text_input("Notes (optional)", key="unload_notes")
            submit_unload = st.form_submit_button("Record Unload")

        if submit_unload:
            if not bin_choice_u or bushels_u <= 0:
                st.error("Please select a bin and enter bushels > 0.")
            else:
                idx = bin_setup.index[bin_setup["Bin"] == bin_choice_u][0]
                current = float(bin_setup.at[idx, "Bushels_in_bin"] or 0.0)
                var_here = str(bin_setup.at[idx, "Variety"] or "").strip()
                if bushels_u > current:
                    st.warning(f"Requested {bushels_u:.1f} bu but only {current:.1f} bu available. Unloading {current:.1f} bu.")
                    take = current
                else:
                    take = bushels_u

                # Update bin
                bin_setup.at[idx, "Bushels_in_bin"] = max(0.0, current - take)
                # If bin is now empty, optionally clear the variety to allow reuse
                if bin_setup.at[idx, "Bushels_in_bin"] == 0.0:
                    # Keep the assigned variety or clear? We'll keep, but offer a checkbox to clear in UI below.
                    pass
                save_bin_setup(bin_setup)

                # Record unload
                new_row_u = {
                    "Timestamp": now_ts(),
                    "Bin": bin_choice_u,
                    "Variety": var_here,
                    "Bushels": float(take),
                    "Destination": destination.strip(),
                    "Notes": notes_u.strip()
                }
                unloads = pd.concat([unloads, pd.DataFrame([new_row_u])], ignore_index=True)
                save_unloads(unloads)

                st.success(f"Unloaded {take:.1f} bu from {bin_choice_u}. Remaining: {bin_setup.at[idx, 'Bushels_in_bin']:.1f} bu.")

        with st.expander("Clear Variety on Empty Bins"):
            empty_bins = bin_setup[(bin_setup["Bushels_in_bin"].fillna(0) == 0) & (bin_setup["Variety"].fillna("") != "")]
            if empty_bins.empty:
                st.info("No empty bins with a set variety.")
            else:
                bins_list = empty_bins["Bin"].tolist()
                bin_to_clear = st.selectbox("Choose empty bin to clear variety", options=bins_list, key="clear_var_bin")
                if st.button("Clear Variety"):
                    idx = bin_setup.index[bin_setup["Bin"] == bin_to_clear][0]
                    bin_setup.at[idx, "Variety"] = ""
                    save_bin_setup(bin_setup)
                    st.success(f"Cleared variety for {bin_to_clear}.")

# ---------- Records ----------
with tab_records:
    st.subheader("Deliveries & Unloads")
    colr1, colr2 = st.columns(2)
    with colr1:
        st.markdown("**Deliveries**")
        if deliveries.empty:
            st.info("No deliveries yet.")
        else:
            st.dataframe(deliveries.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)
    with colr2:
        st.markdown("**Unloads**")
        if unloads.empty:
            st.info("No unloads yet.")
        else:
            st.dataframe(unloads.sort_values("Timestamp", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Export CSVs**")
    colx1, colx2, colx3 = st.columns(3)
    with open(BIN_CSV, "rb") as f:
        colx1.download_button("Download bin_setup.csv", f, file_name="bin_setup.csv")
    with open(DELIVERIES_CSV, "rb") as f:
        colx2.download_button("Download deliveries.csv", f, file_name="deliveries.csv")
    with open(UNLOADS_CSV, "rb") as f:
        colx3.download_button("Download unloads.csv", f, file_name="unloads.csv")


st.caption
