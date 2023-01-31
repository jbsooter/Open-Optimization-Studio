from datetime import datetime, timedelta, time
from io import StringIO

import icalendar
import numpy as np
import pandas as pd
import pytz
import recurring_ical_events
import streamlit as st
from ics import Calendar
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
            x_k.append(solver.IntVar(0,1,'x' + str(i) + str(k)))
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
                if k+ r < 12:
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

    solver.Maximize(obj_exp)
    solver.Solve()

    df_sol = pd.DataFrame()
    df_sol["obj"] = pd.Series(solver.Objective().Value())
    for x in solver.variables():
        if (x.name() != "inequality") & (x.name() != "RHS"):
            df_sol[x.name()] = pd.Series(x.SolutionValue())

    print(df_sol.to_string())

def model_builder():
    cal_df = st.session_state["calendar_df"]
    #cal_df = cal_df[cal_df["begin"] >= datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=pytz.timezone('US/Central'))]
    #cal_df = cal_df[cal_df["end"] <= datetime(day=st.session_state["end_horizon"].day,month=st.session_state["end_horizon"].month,year=st.session_state["end_horizon"].year,tzinfo=pytz.timezone('US/Central'))]
    cal_df["dur"] = cal_df["end"]- cal_df["begin"]
    st.write(cal_df)
    #TODO: convert calendar and task inputs to model math
    st.write("coming soon!")
def import_calendar():
    cal = icalendar.Calendar.from_ical(StringIO(st.session_state["calendar_ics"].getvalue().decode("utf-8")).read())
    events = recurring_ical_events.of(cal).between(datetime.today(),datetime.today() + timedelta(days=14))
    events_dict = [event_to_dict(event) for event in events]
    events_df = pd.DataFrame(events_dict)

    st.session_state["calendar_df"] = events_df
def event_to_dict(event):
    #https://www.youtube.com/watch?v=qRLkAZTc3GE
    return {
        #'name': event["NAME"],
        'begin': datetime(day=int(event["DTSTART"].dt.strftime("%d")),month=int(event["DTSTART"].dt.strftime("%m")),year=int(event["DTSTART"].dt.strftime("%Y")), hour=int(event["DTSTART"].dt.strftime("%H")),minute=int(event["DTSTART"].dt.strftime("%M"))).astimezone(pytz.timezone('US/Central')),
        'end':datetime(day=int(event["DTEND"].dt.strftime("%d")),month=int(event["DTEND"].dt.strftime("%m")),year=int(event["DTEND"].dt.strftime("%Y")), hour=int(event["DTEND"].dt.strftime("%H")),minute=int(event["DTEND"].dt.strftime("%M"))).astimezone(pytz.timezone('US/Central'))
     }
def main():
    st.write("coming soon!")
    st.file_uploader("Upload Calendar",type=".ics",key='calendar_ics',on_change=import_calendar)

    st.date_input("start",value=datetime.today(),key="begin_horizon")
    st.date_input("end",value=datetime.today() + timedelta(days=7), key="end_horizon")

    st.button("Optimize", on_click=model_builder)

if __name__ == "__main__":
    main()