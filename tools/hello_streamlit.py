#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "streamlit",
# ]
# ///
"""
Simple Streamlit test app for deployment verification.
Run with: uv run streamlit run hello_streamlit.py
"""

import streamlit as st
from datetime import datetime
import os
import socket
import sys

# Page config
st.set_page_config(
    page_title="AK6MJ HF Tools - Hello World",
    page_icon="📡",
    layout="wide"
)

# Custom CSS for ham radio aesthetic
st.markdown("""
<style>
    .main {
        background-color: #1a1a1a;
    }
    h1 {
        color: #00ff00;
        font-family: 'Courier New', monospace;
    }
    .stMarkdown {
        color: #00ff00;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📡 AK6MJ HF Propagation Tools")
st.markdown("**Status:** ✅ Online")

# Columns for info
col1, col2 = st.columns(2)

with col1:
    st.subheader("Station Info")
    st.write(f"**Callsign:** AK6MJ")
    st.write(f"**Grid:** CM98kq (Folsom, CA)")
    st.write(f"**Server Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

with col2:
    st.subheader("Deployment Info")
    st.write(f"**Environment:** {os.getenv('STREAMLIT_ENV', 'production')}")
    st.write(f"**Python:** {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    st.write(f"**Host:** {socket.gethostname()}")

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["Overview", "WSPR", "Antenna"])

with tab1:
    st.header("Deployment Test")
    st.success("This page confirms your Streamlit deployment is working!")

    st.subheader("Next Steps")
    st.write("1. ✅ Verify HTTPS is working (if configured)")
    st.write("2. ✅ Test that page refreshes properly")
    st.write("3. ✅ Deploy full antenna analysis dashboard")

    with st.expander("Test Interactivity"):
        name = st.text_input("Your callsign:", "W1AW")
        if st.button("Test Button"):
            st.balloons()
            st.success(f"Hello {name}! 73 from AK6MJ!")

with tab2:
    st.header("WSPR Beacon Control")
    st.info("Coming soon - remote WSPR beacon control")

    # Mock controls
    band = st.selectbox("Band:", ["20m", "40m", "15m", "10m"])
    power = st.slider("Power (dBm):", 0, 30, 23)

    if st.button("Apply Settings (Demo)"):
        st.warning(f"Would set: {band} at {power}dBm")

with tab3:
    st.header("Antenna Analysis")
    st.info("Coming soon - antenna comparison tools")

    # Mock data
    st.subheader("Defined Antennas")
    st.write("• Hustler 6BTV (vertical)")
    st.write("• EFHW 20-10m (horizontal)")

st.divider()

# Footer
st.markdown(f"""
<div style='text-align: center; color: #666; font-size: 0.8em;'>
    🤖 Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
    <a href='https://github.com/bbarclay7/ak6mj-hf-propagation'>GitHub Repo</a>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Navigation")
    st.write("📡 AK6MJ Station")
    st.write("📍 CM98kq")

    st.divider()

    st.subheader("Health Check")
    if st.button("Refresh Status"):
        st.rerun()

    st.metric("Status", "Online", "✓")
    st.metric("Uptime", "N/A")
