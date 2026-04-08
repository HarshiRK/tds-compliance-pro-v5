import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="TDS Compliance Pro V5", layout="wide")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
        # Clean headers and data immediately
        df.columns = [c.strip() for c in df.columns]
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce').fillna(pd.Timestamp('2099-12-31'))
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return None

df = load_data()

if df is not None:
    st.sidebar.title("🛡️ Compliance Engine V5")
    
    # DEBUG MODE (Keep this on while testing with your manager)
    show_debug = st.sidebar.checkbox("Show Debug Info", value=False)
    
    st.title("🏛️ TDS Compliance Professional - V5")
    st.write("---")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Step 1: Payer & Section")
        
        # 1. Section
        sections = sorted(df['Section'].unique().tolist())
        section = st.selectbox("1. Select Section", options=sections)
        f_df = df[df['Section'] == section]
        
        # 2. Payer Category
        payer_types = sorted(f_df['Payer Category'].unique().tolist())
        payer_sel = st.selectbox("2. Payer Category", options=payer_types)
        f_df_payer = f_df[f_df['Payer Category'] == payer_sel]
        
        # 3. Nature of Payment
        natures = sorted(f_df_payer['Nature of Payment'].unique().tolist())
        nature_sel = st.selectbox("3. Nature of Payment", options=natures)
        f_df_nature = f_df_payer[f_df_payer['Nature of Payment'] == nature_sel]
        
        amount = st.number_input("4. Transaction Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        st.subheader("👤 Step 2: Payee Configuration")
        
        # 4. Payee Type (Forced Dropdown)
        payee_options = sorted(f_df_nature['Payee Type'].unique().tolist())
        
        # This line ensures the dropdown shows up if there is ANY data
        payee_sel = st.selectbox("5. Category of Payee", options=payee_options if payee_options else ["Any Resident"])

        pan_status = st.radio("6. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("7. Date of Payment")
        calc_mode = st.radio("8. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target = pd.to_datetime(pay_date)
        
        # Match all filters
        final_match = f_df_nature[f_df_nature['Payee Type'] == payee_sel]
        rule = final_match[(final_match['Effective From'] <= target) & (final_match['Effective To'] >= target)]
        
        if rule.empty and not final_match.empty:
            rule = final_match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                final_rate = 20.0 if pan_status == "No" else base_rate
                tax = (amount * final_rate) / 100
                
                r1, r2, r3 = st.columns(3)
                if amount > thresh:
                    r1.metric("TDS PAYABLE", f"₹{tax:,.2f}", delta="DEDUCT")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="BREACHED")
                    st.success(f"### ✅ CALCULATED TDS: ₹{tax:,.2f}")
                else:
                    r1.metric("CALCULATED TDS", f"₹{tax:,.2f}", delta="NOT APPLICABLE")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="SAFE")
                    st.warning("### ⚠️ TDS NOT APPLICABLE")
                
                with st.expander("📝 View Statutory Reference"):
                    st.info(f"**Legal Note:** {sel['Notes']}")
            except:
                st.error("Excel numeric error.")
        else:
            st.error("No matching rule found in Excel for these selections.")

    # DEBUG SECTION
    if show_debug:
        st.write("### 🔍 Debug: Rows found for this Section & Payer")
        st.write(f_df_payer)
