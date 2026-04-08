import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="TDS Compliance Pro V5", layout="wide")

# Custom CSS for a professional Look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("TDS_Master_Data.xlsx", engine='openpyxl')
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
    st.sidebar.title("🛡️ Compliance V5")
    st.sidebar.success("Pro Edition: Multi-Layer Filtering")
    
    st.title("🏛️ TDS Compliance Professional - V5")
    st.caption(f"System Date: {datetime.now().strftime('%d %B, %Y')}")
    st.write("---")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Step 1: Payer & Section")
        
        # 1. Section Dropdown
        sections = sorted([s for s in df['Section'].unique() if str(s) != 'nan'])
        section = st.selectbox("1. Select Section", options=sections)
        f_df = df[df['Section'] == section]
        
        # 2. Payer Category Dropdown
        payer_types = sorted([p for p in f_df['Payer Category'].unique() if str(p) != 'nan'])
        payer_sel = st.selectbox("2. Payer Category", options=payer_types)
        f_df_payer = f_df[f_df['Payer Category'] == payer_sel]
        
        # 3. Nature of Payment Dropdown
        natures = sorted([n for n in f_df_payer['Nature of Payment'].unique() if str(n) != 'nan'])
        nature_sel = st.selectbox("3. Nature of Payment", options=natures)
        f_df_nature = f_df_payer[f_df_payer['Nature of Payment'] == nature_sel]
        
        amount = st.number_input("4. Transaction Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        st.subheader("👤 Step 2: Payee Configuration")
        
        # --- FIXED PAYEE DROPDOWN LOGIC ---
        # Get all unique payee types for this specific Section + Payer + Nature
        payee_options = sorted([p for p in f_df_nature['Payee Type'].unique() if str(p) != 'nan'])
        
        if len(payee_options) > 1:
            payee_sel = st.selectbox("5. Category of Payee", options=payee_options)
        elif len(payee_options) == 1:
            payee_sel = payee_options[0]
            st.info(f"Payee Category (Auto): **{payee_sel}**")
        else:
            payee_sel = "Any Resident"
            st.warning("No specific Payee Type found in Excel.")

        pan_status = st.radio("6. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("7. Date of Payment")
        calc_mode = st.radio("8. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    # 3. CALCULATION
    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target = pd.to_datetime(pay_date)
        
        # Final match based on all selections
        final_match = f_df_nature[f_df_nature['Payee Type'] == payee_sel]
        
        rule = final_match[(final_match['Effective From'] <= target) & (final_match['Effective To'] >= target)]
        
        if rule.empty and not final_match.empty:
            rule = final_match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # 194C Aggregate Logic
                if section == "194C" and calc_mode == "Aggregate (Full Year)":
                    thresh = 100000.0
                
                final_rate = 20.0 if pan_status == "No" else base_rate
                tax = (amount * final_rate) / 100
                
                r1, r2, r3 = st.columns(3)
                
                if amount > thresh:
                    r1.metric("TDS PAYABLE", f"₹{tax:,.2f}", delta="DEDUCT", delta_color="inverse")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="BREACHED")
                    st.success(f"### ✅ CALCULATED TDS: ₹{tax:,.2f}")
                    st.write(f"**Compliance Note:** TDS is applicable as the amount (₹{amount:,.0f}) exceeds the limit of ₹{thresh:,.0f}.")
                else:
                    r1.metric("CALCULATED TDS", f"₹{tax:,.2f}", delta="NOT APPLICABLE")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="SAFE")
                    st.warning("### ⚠️ TDS NOT APPLICABLE")
                    st.write(f"**Compliance Note:** TDS is **not applicable** because the amount (₹{amount:,.0f}) is below the limit of ₹{thresh:,.0f}.")
                    st.info(f"**Math:** {final_rate}% of ₹{amount:,.0f} is ₹{tax:,.2f}, but threshold not reached.")

                with st.expander("📝 View Statutory Reference"):
                    st.write(f"**Section:** {section} | **Payer:** {payer_sel}")
                    st.write(f"**Nature:** {sel['Nature of Payment']} | **Payee:** {payee_sel}")
                    st.info(f"**Legal Note:** {sel['Notes']}")
            except:
                st.error("Excel Error: Ensure Rate and Threshold are numbers.")
        else:
            st.error("No statutory rule found for this specific date and payee combination.")
