from datetime import datetime, timedelta
from io import StringIO
from math import trunc

import icalendar
import pandas as pd
import recurring_ical_events
import streamlit as st
from calendar_view.calendar import Calendar
from calendar_view.config.style import image_font
from calendar_view.core.config import CalendarConfig
from calendar_view.core.event import EventStyles
from ortools.linear_solver import pywraplp
from calendar_view.config import style

from utilities import timeblockingutils


def generate_time_blocks(I,K,a_k,p_k,r_i,d_i):
    """
    I = number of tasks to complete
    K = number of periods on the planning horizon
    a_k = 1 if period available, o.w 0
    p_k = 1 if period k is not preferred, 2 if period k is preferred
    r_i = required number of 15 min periods to complete task i
    d_i = period that task i is due
    """
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('CP-SAT')

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

    #task must be completed before due date
    for i in range(0,I):
        for k in range(0,K):
            if k >= d_i[i]:
                solver.Add(x_ik[i][k] == 0)

    #maximize the number of tasks completed in a single contiguous stretch
    obj_exp = 0
    for y in y_ik:
        for k in range(0,K):
            obj_exp+= p_k[k]*y[k]

    solver.Maximize(obj_exp)
    status = solver.Solve()

    tz = st.session_state["calendar_df"]["begin"][0].tzinfo
    #print solution and solver status to screen
    #for i in range(0,len(x_ik)):
    #    for k in range(0,K):
    #        if x_ik[i][k].SolutionValue() > 0:
    #            st.write(str(k-1) + " " + str(a_k[k-1]))
    #            st.write(st.session_state[f"task_{i+1}"] + "\t \t" + str((datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz) + timedelta(minutes=(k-1)*15)).astimezone().strftime("%Y-%m-%dT%I:%M:%S  %p %Z")))#todo add timedelta

    st.write(status)
    st.write(solver.Objective().Value())

    #Calendar view test
    #set calendar frame of reference
    begin_list = []
    end_list = []
    for x in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
        begin_time_info = st.session_state[f'hours_{x}'][0].split()
        if begin_time_info[1] == 'AM':
            begin_list.append(int(begin_time_info[0]))
        elif begin_time_info[1] == 'PM':
            begin_list.append(int(begin_time_info[0]) + 12)

        end_time_info = st.session_state[f'hours_{x}'][1].split()
        if end_time_info[1] == 'AM':
            end_list.append(int(end_time_info[0]))
        elif end_time_info[1] == 'PM':
            end_list.append(int(end_time_info[0]) + 12)

    #style of calendar (overrides)
    style.hour_height = 120
    style.event_notes_color = 'black'
    style.event_title_margin = 5
    style.event_title_font = image_font(35)

    config = CalendarConfig(
        lang='en',
        title='Task Schedule',
        dates=st.session_state['begin_horizon'].isoformat() + ' - '+st.session_state['end_horizon'].isoformat(),
        hours = str(min(begin_list)-1) + " - " + str(max(end_list)+1),
        show_date=True,
        legend=False,
       title_vertical_align='top',
    )
    task_calendar = Calendar.build(config)
    for i in range(0,len(x_ik)):
        pd_start_list = []
        for k in range(0,K):
            if x_ik[i][k].SolutionValue() >0:

                dateTimeObj = (datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz) + timedelta(minutes=(k-1)*15))
                pd_start_list.append(dateTimeObj)

                #st.write(dateTimeObj.time().strftime('%H:%M'))

        #Support discontinous work periods
        #track start index of latest work period
        start_index = 0
        #iterate all start dates for current task
        for j in range(0,len(pd_start_list)):
            #split blocks if indicated by greater than 15 min diff in start time
            if(pd_start_list[j] - pd_start_list[j-1] > timedelta(minutes=15)):
                start = min(pd_start_list[start_index:j])
                end = max(pd_start_list[start_index:j]) + timedelta(minutes=15)

                task_calendar.add_event(
                    title = st.session_state[f'task_{i+1}'],
                    day=start.date(),
                    start = start.time().strftime('%H:%M%Z'),
                    end = end.time().strftime('%H:%M%Z'),
                    style = EventStyles.GREEN,
                    notes=start.time().strftime('%I:%M %p %Z') + ' - ' + end.time().strftime('%I:%M %p %Z')
                    )
                #set start index for next round to be after this block
                start_index = j

            #if last index (j) and there has been a prior block for the task
            if (j == len(pd_start_list)-1) &( start_index != 0):
                start = pd_start_list[-1]
                end = pd_start_list[-1] + timedelta(minutes=15)

                task_calendar.add_event(
                    title = st.session_state[f'task_{i+1}'],
                    day=start.date(),
                    start = start.time().strftime('%H:%M%Z'),
                    end = end.time().strftime('%H:%M%Z'),
                    style = EventStyles.GREEN,
                    notes=start.time().strftime('%I:%M %p %Z') + ' - ' + end.time().strftime('%I:%M %p %Z')
                )
            #if j is last elements index and there has been no prior block
            if (j == len(pd_start_list)-1) &( start_index == 0):
                start = pd_start_list[0]
                end = pd_start_list[-1] + timedelta(minutes=15)

                task_calendar.add_event(
                    title = st.session_state[f'task_{i+1}'],
                    day=start.date(),
                    start = start.time().strftime('%H:%M%Z'),
                    end = end.time().strftime('%H:%M%Z'),
                    style = EventStyles.GREEN,
                    notes=start.time().strftime('%I:%M %p %Z') + ' - ' + end.time().strftime('%I:%M %p %Z')
                )

            #remove events that are not within the timeframe
            cal_df = st.session_state["calendar_df"]
            cal_df = cal_df[cal_df["begin"] >= datetime(day=st.session_state["begin_horizon"].day,month=st.session_state["begin_horizon"].month,year=st.session_state["begin_horizon"].year,tzinfo=tz)]
            cal_df = cal_df[cal_df["end"] <= datetime(day=st.session_state["end_horizon"].day,month=st.session_state["end_horizon"].month,year=st.session_state["end_horizon"].year,tzinfo=tz)]

            #add calendar events to time block png
            for index, row in cal_df.iterrows():
                task_calendar.add_event(
                    title = row["name"],
                    day=row["begin"].date(),
                    start = row["begin"].time().strftime('%H:%M%Z'),
                    end = row["end"].time().strftime('%H:%M%Z'),
                    style = EventStyles.BLUE,
                    notes=row["begin"].time().strftime('%I:%M %p %Z') + ' - ' + row["end"].time().strftime('%I:%M %p %Z')
                )

    task_calendar.save('images/time_blocks.png')
    st.image('images/time_blocks.png')


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
    horizon_length_mins = (horizon_length_days.days+1)*24*60 #inclusive of start end days
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


    # list for if a period is a prefered work period, or not
    p_k = [1]*int(num_periods)

    #get day of week of start of time horion
    current_day = st.session_state["begin_horizon"].weekday()
    #period in day tracker
    period_in_day = 0
    #forall periods on horizon
    for k in range(0,int(num_periods)):
        #none before working hours
        #if period_in_day < timeblockingutils.working_hour_str_to_num(st.session_state[f'hours_{timeblockingutils.day_of_week_int_to_str(current_day)}'][0])*4:
        if period_in_day < timeblockingutils.working_hour_str_to_num(st.session_state[f'hours_{timeblockingutils.day_of_week_int_to_str(current_day)}'][0])*4:
           #st.write( timeblockingutils.working_hour_str_to_num(st.session_state[f'hours_{timeblockingutils.day_of_week_int_to_str(current_day)}'][0])*4)
           a_k[k] =0

        #none after working hours
        if period_in_day >= timeblockingutils.working_hour_str_to_num(st.session_state[f'hours_{timeblockingutils.day_of_week_int_to_str(current_day)}'][1])*4:
            #st.write(period_in_day)
            #st.write( timeblockingutils.working_hour_str_to_num(st.session_state[f'hours_{timeblockingutils.day_of_week_int_to_str(current_day)}'][1])*4)
            a_k[k]  = 0

        #if day is not a workday then make it unavailable
        for weekday in range(0,7):
            #st.write(weekday)
            if (current_day == weekday) & (st.session_state[f"workday_{timeblockingutils.day_of_week_int_to_str(weekday)}"] is False):
                a_k[k] = 0
            #if a day is preferred, double its value in the objective
            if (current_day == weekday) & (st.session_state[f"preferred_{timeblockingutils.day_of_week_int_to_str(weekday)}"] is True):
                p_k[k] = 2

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
        r_i.append(timeblockingutils.time_increment_to_num_periods(st.session_state[f"task_{x+1}_time"]))

    #create due date in terms of period
    d_i = []
    for x in range(0,st.session_state['number_of_tasks']):
        #difference between due date and begin horizon date + 1 day. 24*4 is the plus one day in periods and exists because due dates are
        #assumed to be EOD
        d_i.append(trunc(((st.session_state[f'task_{x+1}_due'] - st.session_state['begin_horizon']).total_seconds()/60)/15) + 24*4)

    generate_time_blocks(st.session_state['number_of_tasks'],int(num_periods),a_k,p_k,r_i,d_i)

def import_calendar():
    if st.session_state.calendar_ics is None:
        #do not access buffer if this callback is the result of user deleting upload file
        return

    #read in ics file, convert to dataframe using event to dict and list comprehension
    cal = icalendar.Calendar.from_ical(StringIO(st.session_state["calendar_ics"].getvalue().decode("utf-8")).read())
    #Date range is the forward looking year
    events = recurring_ical_events.of(cal).between(datetime.today()-timedelta(days=1),datetime.today() + timedelta(days=365))
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

def add_task():
    st.session_state["number_of_tasks"] = st.session_state["number_of_tasks"] + 1
def main():
    st.set_page_config(layout="wide")
    #upload ics file
    st.file_uploader("Upload Calendar",type=".ics",key='calendar_ics',on_change=import_calendar)

    #input planning horizon
    st.date_input("Start",value=datetime.today(),key="begin_horizon")
    st.date_input("End",value=datetime.today() + timedelta(days=7), key="end_horizon")

    work_time_expander = st.expander(label="Change Working Days/Hours",expanded=True)

    with work_time_expander:
        #create work day and time insertion
        for x in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
            col1,col2 = st.columns([1,3])
            with col1:
                if x in ['Saturday','Sunday']:
                    st.checkbox(label=x, key=('workday_'+x),value=False)
                else:
                    st.checkbox(label=x, key=('workday_'+x),value=True)

                st.checkbox(label="Preferred Day",key=('preferred_' + x))
            with col2:
                st.select_slider(label='Working Hours',key=('hours_'+x),options=timeblockingutils.working_hours_list,value=('8 AM', '5 PM'))

    #create task insertion
    if 'number_of_tasks' not in st.session_state:
        st.session_state['number_of_tasks'] = 1

    for x in range(0,st.session_state['number_of_tasks']):
        col1,col2,col3 = st.columns([1,1,1])
        with col1:
            st.text_input(label='Task Name',value=f"Task {x+1}",key=f"task_{x+1}")
        with col2:
            st.selectbox(label='Task Length',options=timeblockingutils.time_increments_list,key=f"task_{x+1}_time",index=3)
        with col3:
            st.date_input(label="Due EOD",value=st.session_state["end_horizon"],key=f"task_{x+1}_due")

    st.button(label="Add Task", on_click=add_task)
    #run optimization model
    st.button("Create Time Blocks", on_click=model_builder)


if __name__ == "__main__":
    main()