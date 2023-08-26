import datetime

import pandas as pd
import streamlit as st

def add_employee_line(col1,col2,col3):
    with col1:
        st.text_input(label="Employee Name")
    with col2:
        st.select_slider(label= "Hours Available", options=st.session_state.business_hours, value=[st.session_state.business_hours[0], st.session_state.business_hours[-1]])
    with col3:
        st.multiselect(label="On Days", options=st.session_state.business_days)
def main():
    st.subheader("Scheduling")
    st.write("Coming Soon!")

if __name__ == "__main__":
    main()