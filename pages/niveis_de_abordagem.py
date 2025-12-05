import pandas as pd
import streamlit as st


def espessura_minima(P, Do, SEW, Py, A):
    tm = ((P*Do)/(2*(SEW+Py))) + A
    return tm



a = st.selectbox("Entre com um ", [1,2])

confusion_matrix = pd.DataFrame(
    {
        "Predicted Cat": [85, 3, 2, 1],
        "Predicted Dog": [2, 78, 4, 0],
        "Predicted Bird": [1, 5, 72, 3],
        "Predicted Fish": [0, 2, 1, a],
    },
    index=["Actual Cat", "Actual Dog", "Actual Bird", "Actual Fish"],
)
st.table(confusion_matrix)