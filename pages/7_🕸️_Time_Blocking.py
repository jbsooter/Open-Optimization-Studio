from datetime import datetime, timedelta
from io import StringIO
from math import trunc

import icalendar
import pandas as pd
import recurring_ical_events
import streamlit as st
from ortools.linear_solver import pywraplp

def generate_time_blocks(I,K,a_k,r_i):
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')

    #I = 5 #num tasks will be generated from input
    #K = 12 #num_periods will be generated from calendar window and working hours

    #a_k = [0,0,0,1,1,1,1,1,1,1,1,1] #allowed periods (will be generated from calendar
    #r_i = [2,1,1,2,1] #required number of periods to complete task i


    x_ik = [] #is task i worked on during period k?
    for i in range(0,I):
        x_k = []
        for k in range(0,K):
            x_k.append(solver.IntVar(0,1,'x' + str(i) + " " + str(k)))
        x_ik.append(x_k)

    #is task i worked on during a cohesive block starting with period k?
    y_ik = []
    for i in range (0,I):
        y_k = []
        for k in range(0,K):
            y_k.append(solver.IntVar(0,1,'y' + str(i) + str(k)))
        y_ik.append(y_k)

    #togetherness constraint
    for k in range(0,K):
        for i in range(0,I):
            const_exp = 0
            for r in range(0,r_i[i]):
                if k+ r < K:
                    const_exp += x_ik[i][k+r]
            solver.Add(const_exp >= r_i[i]*y_ik[i][k])

    #time period available constraint
    for i in range(0,I):
        for k in range(0,K):
            solver.Add(a_k[k] >= x_ik[i][k])
    obj_exp = 0
    for y in y_ik:
        for z in y:
            obj_exp+= z

    #task single completion constraint
    for i in range(0,I):
        constraint_e = 0
        for k in range(0,K):
            constraint_e += x_ik[i][k]
        solver.Add(constraint_e == r_i[i])

    #maximize the number of tasks completed in a single contiguous stretch
    solver.Maximize(obj_exp)
    status = solver.Solve()

    #create dataframe to store output and only print if the variable is 1
    df_sol = pd.DataFrame()
    df_sol["obj"] = pd.Series(solver.Objective().Value())
    for x in solver.variables():
        if (x.SolutionValue()  ==1):
            df_sol[x.name()] = pd.Series(x.SolutionValue())

    st.write(df_sol)
    st.write(status)

def model_builder():
    #retrieve calendar dataframe from session state
    cal_df = st.session_state["calendar_df"]

    #remove events that are not within the timeframe
    cal_df = cal_df[cal_df["begin"] >= st.session_state["begin_horizaon"]]
    cal_df = cal_df[cal_df["end"] <= st.session_state["end_horizon"]]

    #create event duration column
    cal_df["dur"] = cal_df["end"]- cal_df["begin"]

    #calculate timedelta between beginning of horizon and beginning/end of event
    cal_df["bpd"] = cal_df["begin"] - st.session_state["begin_horizon"]
    cal_df["epd"] = cal_df["end"] - st.session_state["begin_horizon"]

    #transform the timedelta between beginning of horizon and beginning of event to a period index
    period = []
    for index, row in cal_df.iterrows():
        period.append(trunc((row["bpd"].total_seconds()/60)/15))
    cal_df["begin_pd"] = period

    #transform the timedelta between beginning of horizon and end of event to a period index
    period = []
    for index, row in cal_df.iterrows():
        period.append(trunc((row["epd"].total_seconds()/60)/15))
    cal_df["end_pd"] = period

    #calculate number of 15 minute periods on planning horizon
    horizon_length_days = st.session_state["end_horizon"] - st.session_state["begin_horizon"]
    horizon_length_mins = horizon_length_days.days*24*60
    num_periods = horizon_length_mins/15
    st.write(horizon_length_days)

    #build list for period availability, making period unavailable if alread unoccupied by event
    a_k = []
    off_calc = 0
    for k in range(0,int(num_periods)):
        avail = 0
        for index, row in cal_df.iterrows():
            if (k >= row["begin_pd"]) &( k <= row["end_pd"]):
                avail = 0
                break
            else:
                avail = 1
        a_k.append(avail)

    #make a period unavailable if it is before 8 AM or after 8 PM
    for k in range(0,int(num_periods)):
        #none before 8 AM
        if off_calc < 8*4:
            a_k[k] =0

        #none after 8 PM
        if off_calc > 20*4:
            a_k[k]  = 0
        if(off_calc < 24*4):
            off_calc += 1
        else:
            off_calc = 0

    #solve the model
    generate_time_blocks(3,int(num_periods),a_k,[1,2,16])

def import_calendar():
    if st.session_state.calendar_ics is None:
        #do not access buffer if this callback is the result of user deleting upload file
        return

    cal = icalendar.Calendar.from_ical(StringIO(st.session_state["calendar_ics"].getvalue().decode("utf-8")).read())
    events = recurring_ical_events.of(cal).between(datetime.today(),datetime.today() + timedelta(days=14))
    events_dict = [event_to_dict(event) for event in events]
    events_df = pd.DataFrame(events_dict)

    st.write(events_df)
    st.session_state["calendar_df"] = events_df
def event_to_dict(event):
    #st.write(event["DTSTART"].dt.tzinfo)
    #https://www.youtube.com/watch?v=qRLkAZTc3GE
    return {
        'name': event["SUMMARY"],
        'begin': event["DTSTART"].dt,
        'end':event["DTEND"].dt
     }
def main():
    st.write("coming soon!")
    st.file_uploader("Upload Calendar",type=".ics",key='calendar_ics',on_change=import_calendar)

    st.date_input("start",value=datetime.today(),key="begin_horizon")
    st.date_input("end",value=datetime.today() + timedelta(days=7), key="end_horizon")

    st.button("Optimize", on_click=model_builder)

if __name__ == "__main__":
    main()