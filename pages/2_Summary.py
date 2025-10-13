import streamlit as st
from datetime import date
current_date = (date.today()).strftime("%m/%d/%Y")
st.title("#Comment Summary")
st.write("Summary")
st.write("From the video the general summary is as follows: ")
st.write("Summary goes here...")
st.write(f"Generated on {current_date}")