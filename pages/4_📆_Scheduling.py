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

    #st.write("UI layout only. No backend. ")

    #col1, col2,col3 = st.columns([1,3,1])
    #with col1:
    #    st.text_input(label="Business Name")
    #with col2:
    #    time_list = [f'{x} AM' for x in range(1,12)]
    #    time_list.extend(["12 PM"])
    #    time_list.extend([f'{x} PM' for x in range(1,12)])
    #    time_list.extend(["12 AM"])
    #    st.select_slider(label= "Open Hours", options=time_list, value=['1 AM', '12 AM'], key='business_hours')
    #with col3:
    #    st.multiselect(label="On Days", options=["Mon","Tues","Wed","Thurs","Fri","Sat","Sun"], key ="business_days")

    #st.header("Employee Availability")

    #col1, col2,col3 = st.columns([1,3,1])
    #add_employee_line(col1,col2,col3)

if __name__ == "__main__":
    main()