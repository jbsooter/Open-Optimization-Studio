from datetime import datetime, timedelta
from io import StringIO
from math import trunc

import icalendar
import pandas as pd
import recurring_ical_events
import streamlit as st
from ortools.linear_solver import pywraplp

import utilities.dateutils
from utilities import dateutils


def generate_time_blocks(I,K,a_k,r_i):
    """
    I = number of tasks to complete
    K = number of periods on the planning horizon
    a_k = 1 if period available, o.w 0
    r_i = required number of 15 min periods to complete task i
    """
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')

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

    #one task per period
    for k in range(0,K):
        constraint = 0
        for i in range(0,I):
            constraint+= x_ik[i][k]
        solver.Add(constraint <= 1)

    #maximize the number of tasks completed in a single contiguous stretch
    solver.Maximize(obj_exp)
    status = solver.Solve()

    tz = st.session_state["calendar_df"]["begin"][0].tzinfo
    #print solution and solver status to screen
    for i in range(0,len(x_ik)):
        for k in range(0,K):
            if x_ik[i][k].SolutionValue() > 0:
                st.write(st.session_state[f"task_{i+1}"] + "\t \t" + str((datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz) + timedelta(minutes=(k-1)*15)).astimezone().strftime("%Y-%m-%dT%I:%M:%S  %p %Z")))#todo add timedelta
                #st.write(str(i) + "\t \t" + str((datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz) + timedelta(minutes=(k)*15))))
    st.write(status)
    st.write(solver.Objective().Value())

def model_builder():
    #retrieve calendar dataframe from session state
    cal_df = st.session_state["calendar_df"]

    #retrieve cal time zone
    tz = cal_df["begin"][0].tzinfo
    #remove events that are not within the timeframe
    cal_df = cal_df[cal_df["begin"] >= datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz)]
    cal_df = cal_df[cal_df["end"] <= datetime(day=st.session_state["end_horizon"].day,month=st.session_state["end_horizon"].month,year=st.session_state["end_horizon"].year,tzinfo=tz)]
    #create event duration column
    cal_df["dur"] = cal_df["end"]- cal_df["begin"]

    #calculate timedelta between beginning of horizon and beginning/end of event
    cal_df["bpd"] = cal_df["begin"] - datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz)
    cal_df["epd"] = cal_df["end"] - datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz)

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

    #build list for period availability, making period unavailable if alread unoccupied by calendar event
    a_k = []

    for k in range(0,int(num_periods)):
        avail = 0
        for index, row in cal_df.iterrows():
            if (k >= row["begin_pd"]) &( k <= row["end_pd"]):
                avail = 0
                break
            else:
                avail = 1
        a_k.append(avail)

    #get day of week of start of time horion
    current_day = st.session_state["begin_horizon"].weekday()
    #period in day tracker
    period_in_day = 0
    #forall periods on horizon
    for k in range(0,int(num_periods)):
        #none before working hours
        if period_in_day < dateutils.working_hour_str_to_num(st.session_state[f'hours_{dateutils.day_of_week_int_to_str(current_day)}'][0])*4:
            a_k[k] =0

        #none after working hours
        if period_in_day >= dateutils.working_hour_str_to_num(st.session_state[f'hours_{dateutils.day_of_week_int_to_str(current_day)}'][1])*4:
            a_k[k]  = 0

        #if day is not a workday then make it unavailable
        for weekday in range(0,7):
            if (current_day == weekday) & (st.session_state[f"workday_{dateutils.day_of_week_int_to_str(weekday)}"] is False):
                a_k[k] = 0

        #increment period within day if there are periods remaining
        if(period_in_day < 24*4):
            period_in_day += 1
        #else adjust current day and reset period in day to 0
        else:
            period_in_day = 0
            #if at end of integer range, reset to Monday (0)
            if(current_day >=6):
                current_day = 0
            #else increment the day of week
            else:
                current_day += 1

    #solve the model with sample 3 tasks, num_periods, a_k, and 1,2,3 task lengths
    r_i = []
    for x in range(0,st.session_state['number_of_tasks']):
        r_i.append(dateutils.time_increment_to_num_periods(st.session_state[f"task_{x+1}_time"]))
    generate_time_blocks(st.session_state['number_of_tasks'],int(num_periods),a_k,r_i)

def import_calendar():
    if st.session_state.calendar_ics is None:
        #do not access buffer if this callback is the result of user deleting upload file
        return

    #read in ics file, convert to dataframe using event to dict and list comprehension
    cal = icalendar.Calendar.from_ical(StringIO(st.session_state["calendar_ics"].getvalue().decode("utf-8")).read())
    #TODO: Evaluate options for import DATERANGE
    events = recurring_ical_events.of(cal).between(datetime.today()-timedelta(days=1),datetime.today() + timedelta(days=14))
    events_dict = [event_to_dict(event) for event in events]
    events_df = pd.DataFrame(events_dict)

    #write df to screen and save to session state
    st.write(events_df)
    st.session_state["calendar_df"] = events_df
def event_to_dict(event):
    #https://www.youtube.com/watch?v=qRLkAZTc3GE
    return {
        'name': event["SUMMARY"],
        'begin': event["DTSTART"].dt,
        'end':event["DTEND"].dt
     }
def main():
    #upload ics file
    st.file_uploader("Upload Calendar",type=".ics",key='calendar_ics',on_change=import_calendar)

    #input planning horizon
    st.date_input("Start",value=datetime.today(),key="begin_horizon")
    st.date_input("End",value=datetime.today() + timedelta(days=7), key="end_horizon")

    #create work day and time insertion
    for x in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
        col1,col2 = st.columns([1,3])
        with col1:
            st.checkbox(label=x, key=('workday_'+x))
            st.write(' ')
        with col2:
            st.select_slider(label='Working Hours',key=('hours_'+x),options=utilities.dateutils.working_hours_list,value=('8 AM', '5 PM'))

    #create task insertion
    if 'number_of_tasks' not in st.session_state:
        st.session_state['number_of_tasks'] = 3

    for x in range(0,st.session_state['number_of_tasks']):
        col1,col2 = st.columns([1,1])
        with col1:
            st.text_input(label='Task Name',value=f"Task {x+1}",key=f"task_{x+1}")
        with col2:
            st.selectbox(label='Task Length',options=dateutils.time_increments_list,key=f"task_{x+1}_time")
    #run optimization model
    st.button("Create Time Blocks", on_click=model_builder)


if __name__ == "__main__":
    main()