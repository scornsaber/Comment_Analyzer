import streamlit as st
from datetime import date
current_date = (date.today()).strftime("%m/%d/%Y")
st.title("#Sentiment Analysis")
st.write("Sentiment Analysis")
st.write("From the video the general sentiment is as follows: ")
st.write("Sentiment goes here...")
st.write(f"Generated on {current_date}")