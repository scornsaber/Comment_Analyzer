import streamlit as st
import pandas as pd
from numpy.random import default_rng as rng
st.title("#Dashboards")
st.write("Dashboards")
#bar chart example
df = pd.DataFrame(rng(0).standard_normal((20, 3)), columns=["a", "b", "c"])
st.bar_chart(df)