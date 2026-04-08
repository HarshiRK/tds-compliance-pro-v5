import streamlit as st
import pandas as pd
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="TDS Compliance Pro V5", layout="wide")

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
    st.sidebar.title("🛡️ Compliance Engine V5")
    st.sidebar.info("Harshita's Pro Model")
    
    st.title("🏛️ TDS Compliance Professional - V5")
    st.write("---")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📋 Step 1: Transaction Details")
        
        # 1. SECTION
        sections = sorted(df['Section'].unique().tolist())
        section = st.selectbox("1. Select Section", options=sections)
        f_df = df[df['Section'] == section]
        
        # 2. PAYER (New feature for 194A)
        payer_types = sorted(f_df['Payer Category'].unique().tolist())
        payer_sel = st.selectbox("2. Payer Category", options=payer_types)
        f_df_payer = f_df[f_df['Payer Category'] == payer_sel]
        
        # 3. NATURE
        natures = sorted(f_df_payer['Nature of Payment'].unique().tolist())
        nature_sel = st.selectbox("3. Nature of Payment", options=natures)
        
        amount = st.number_input("4. Amount (INR)", min_value=0.0, value=250000.0)

    with col2:
        st.subheader("👤 Step 2: Payee Details")
        
        # --- FIXED PAYEE LOGIC ---
        # Instead of filtering by Nature, we show ALL Payees available for this Section/Payer
        # This ensures 'Individual' and 'Others' both show up for 194C
        all_payees = sorted(f_df_payer['Payee Type'].unique().tolist())
        payee_sel = st.selectbox("5. Category of Payee", options=all_payees)

        pan_status = st.radio("6. PAN Available?", ["Yes", "No"], horizontal=True)
        pay_date = st.date_input("7. Date of Payment")
        calc_mode = st.radio("8. Threshold Basis", ["Single Transaction", "Aggregate (Full Year)"], horizontal=True)

    st.write("---")

    if st.button("🚀 EXECUTE COMPLIANCE CHECK", use_container_width=True):
        target = pd.to_datetime(pay_date)
        
        # FINAL MATCH: Section + Payer + Nature + Payee
        final_match = f_df_payer[
            (f_df_payer['Nature of Payment'] == nature_sel) & 
            (f_df_payer['Payee Type'] == payee_sel)
        ]
        
        rule = final_match[(final_match['Effective From'] <= target) & (final_match['Effective To'] >= target)]
        
        # Fallback if date is slightly off
        if rule.empty and not final_match.empty:
            rule = final_match.sort_values(by='Effective From', ascending=False).head(1)

        if not rule.empty:
            sel = rule.iloc[0]
            try:
                base_rate = float(sel['Rate of TDS (%)'])
                thresh = float(sel['Threshold Amount (Rs)'])
                
                # Special 194C Aggregate Logic
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
                    st.write(f"Reason: Amount is below the limit of ₹{thresh:,.0f}")

                with st.expander("📝 View Statutory Details"):
                    st.write(f"**Section:** {section} | **Payer:** {payer_sel}")
                    st.info(f"**Note:** {sel['Notes']}")
            except:
                st.error("Excel numeric error in Rate or Threshold columns.")
        else:
            st.error("No matching rule found. Please check if your Excel has a row for this Payee Category.")
