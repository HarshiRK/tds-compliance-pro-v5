import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP & STYLE
st.set_page_config(page_title="TDS Compliance Pro V5", layout="wide")

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        # Load the Excel file
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        
        # Clean headers (removes hidden spaces)
        df.columns = [c.strip() for c in df.columns]
        
        # Clean text in columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # FIXED DATE LOGIC - This handles the error from your screenshot
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce', format='mixed')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce', format='mixed').fillna(pd.Timestamp('2099-12-31'))
        
        # Remove any rows where Section is missing
        df = df[df['Section'] != 'nan']
        
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}. Please check if your column names match exactly.")
        return None

df = load_data()

if df is not None:
    st.sidebar.title("🛡️ Compliance Engine V5")
    st.sidebar.success("Date-Sensitive Mode: ON")
    st.sidebar.info("Developed by Harshita")
    
    st.title("🏛️ TDS Compliance Professional - V5")
    st.caption(f"System Date: {datetime.now().strftime('%d %B, %Y')} | Data Source: TDS_Master_Data.xlsx")
    st.write("---")

    # 2. INPUT AREA
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Step 1: Transaction Details")
        
        # Section Filter
        sections = sorted(df['Section'].unique().tolist())
        section = st.selectbox("1. Select Section", options=sections)
        f_df = df[df['Section'] == section]
        
        # Payer Category Filter
        payer_types = sorted(f_df['Payer Category'].unique().tolist())
        payer_sel = st.selectbox("2. Payer Category", options=payer_types)
        f_df_payer = f_df[f_df['Payer Category'] == payer_sel]
        
        # Nature Filter
        natures = sorted(f_df_payer['Nature of Payment'].unique().tolist())
        nature_sel = st.selectbox("3. Nature of Payment", options=natures)
        f_df_nature = f_df_payer[f_df_payer['Nature of Payment'] == nature_sel]
        
        amount = st.number_input("4. Transaction Amount (INR)", min_value=0.0, value=300000.0)

    with col2:
        st.subheader("👤 Step 2: Payee Details")
        
        # Payee Dropdown Logic (Shows all payees for this section/payer)
        all_payees = sorted(f_df_payer['Payee Type'].unique().tolist())
        payee_sel = st.selectbox("5. Category of Payee", options=all_payees)

        pan_status = st.radio("6. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("7. Date of Payment")
        calc_mode = st.radio("8. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    # 3. CALCULATION ENGINE
    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target_date = pd.to_datetime(pay_date)
        
        # Final Row Matching
        final_match = f_df_payer[
            (f_df_payer['Nature of Payment'] == nature_sel) & 
            (f_df_payer['Payee Type'] == payee_sel)
        ]
        
        # Date Logic for 194LA and other threshold changes
        rule = final_match[
            (final_match['Effective From'] <= target_date) & 
            (final_match['Effective To'] >= target_date)
        ]
        
        if not rule.empty:
            sel = rule.sort_values(by='Effective From', ascending=False).iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # Special Aggregate Override for 194C
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                # PAN Logic
                final_rate = 20.0 if pan_status == "No" else base_rate
                tax = (amount * final_rate) / 100
                
                # DASHBOARD RESULTS
                r1, r2, r3 = st.columns(3)
                if amount > thresh:
                    r1.metric("TDS PAYABLE", f"₹{tax:,.2f}", delta="DEDUCT", delta_color="inverse")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="BREACHED")
                    st.success(f"### ✅ CALCULATED TDS: ₹{tax:,.2f}")
                    st.write(f"**Compliance Note:** TDS is applicable as the amount (₹{amount:,.0f}) exceeds the statutory limit of ₹{thresh:,.0f}.")
                else:
                    r1.metric("CALCULATED TDS", f"₹{tax:,.2f}", delta="NOT APPLICABLE")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="SAFE")
                    st.warning("
