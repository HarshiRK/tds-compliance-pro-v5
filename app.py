import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP & STYLE
st.set_page_config(page_title="TDS Compliance Pro V5", layout="wide")

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
        
        # FIXED DATE LOGIC
        df['Effective From'] = pd.to_datetime(df['Effective From'], errors='coerce', format='mixed')
        df['Effective To'] = pd.to_datetime(df['Effective To'], errors='coerce', format='mixed').fillna(pd.Timestamp('2099-12-31'))
        df = df[df['Section'] != 'nan']
        return df
    except Exception as e:
        st.error(f"Excel Error: {e}")
        return None

df = load_data()

if df is not None:
    st.sidebar.title("🛡️ Compliance Engine V5")
    st.sidebar.success("Date-Sensitive Mode: ON")
    st.sidebar.info("Developed by Harshita")
    
    st.title("🏛️ TDS Compliance Professional - V5")
    st.caption(f"System Date: {datetime.now().strftime('%d %B, %Y')}")
    st.write("---")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Step 1: Transaction Details")
        sections = sorted(df['Section'].unique().tolist())
        section = st.selectbox("1. Select Section", options=sections)
        f_df = df[df['Section'] == section]
        
        payer_types = sorted(f_df['Payer Category'].unique().tolist())
        payer_sel = st.selectbox("2. Payer Category", options=payer_types)
        f_df_payer = f_df[f_df['Payer Category'] == payer_sel]
        
        natures = sorted(f_df_payer['Nature of Payment'].unique().tolist())
        nature_sel = st.selectbox("3. Nature of Payment", options=natures)
        f_df_nature = f_df_payer[f_df_payer['Nature of Payment'] == nature_sel]
        
        amount = st.number_input("4. Transaction Amount (INR)", min_value=0.0, value=300000.0)

    with col2:
        st.subheader("👤 Step 2: Payee Details")
        all_payees = sorted(f_df_payer['Payee Type'].unique().tolist())
        payee_sel = st.selectbox("5. Category of Payee", options=all_payees)

        pan_status = st.radio("6. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("7. Date of Payment")
        calc_mode = st.radio("8. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target_date = pd.to_datetime(pay_date)
        final_match = f_df_payer[
            (f_df_payer['Nature of Payment'] == nature_sel) & 
            (f_df_payer['Payee Type'] == payee_sel)
        ]
        
        rule = final_match[
            (final_match['Effective From'] <= target_date) & 
            (final_match['Effective To'] >= target_date)
        ]
        
        if not rule.empty:
            sel = rule.sort_values(by='Effective From', ascending=False).iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
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
                    st.write(f"**Compliance Note:** TDS is applicable as the amount (₹{amount:,.0f}) exceeds the statutory limit of ₹{thresh:,.0f}.")
                else:
                    r1.metric("CALCULATED TDS", f"₹{tax:,.2f}", delta="NOT APPLICABLE")
                    r2.metric("RATE", f"{final_rate}%")
                    r3.metric("THRESHOLD", f"₹{thresh:,.0f}", delta="SAFE")
                    st.warning("### ⚠️ STATUS: TDS NOT APPLICABLE")
                    st.write(f"**Compliance Note:** No deduction is required because the amount (₹{amount:,.0f}) is below the threshold of **₹{thresh:,.0f}**.")
                    st.info(f"**Math Breakdown:** At {final_rate}%, the calculated TDS would be ₹{tax:,.2f} if the threshold were reached.")

                with st.expander("📝 View Statutory Reference"):
                    st.write(f"**Section:** {section} | **Effective Range:** {sel['Effective From'].date()} to {sel['Effective To'].date()}")
                    st.info(f"**Legal Note:** {sel['Notes']}")
            except Exception as e:
                st.error("Error calculating results. Check Excel format.")
        else:
            st.error("No statutory rule found for this date. Check Excel ranges.")
