import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
import streamlit as st
from numpy.random import default_rng as rng

#need to do pip install streamlit[charts]


st.title("#Dashboards")
st.write("Dashboards")

#bar chart example
df = pd.DataFrame(rng(0).standard_normal((20, 3)), columns=["a", "b", "c"])
st.bar_chart(df)

#line chart

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=[1, 2, 3, 4, 5],
        y=[1, 3, 2, 5, 4]
    )
)

st.plotly_chart(fig, config = {'scrollZoom': True})

#scatter chart 

df = px.data.iris()
fig = px.scatter(df, x="sepal_width", y="sepal_length")

event = st.plotly_chart(fig, key="iris", on_select="rerun")
