import io

import numpy as np
import streamlit as st
import pandas as pd
import operator
from st_aggrid import AgGrid, GridOptionsBuilder
from ortools.linear_solver import pywraplp

def load_obj_grid(df):
    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df,editable=True)
    builder.configure_column("obj", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["min","max"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True,height=65)

def load_constraints_grid(df):

    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df, editable=True)
    builder.configure_column("inequality", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["<=",">=","=","<",">"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True)

def add_row():
    #get existing
    old_df = st.session_state['df_mip']

    #create dataframe representing new row
    new_row = pd.DataFrame()
    for col in old_df.columns:
        new_row[col] = [0]

    #create and save new, combined dataframe
    st.session_state['df_mip'] = pd.concat([old_df, new_row])

def add_column():
    #get old data
    old_df = st.session_state['df_mip']

    #row and column lengths
    nrows = len(old_df)
    ncols = len(old_df.columns)

    #create new row with auto variable name
    st.session_state['df_mip'].insert(ncols-2,f"var{ncols}",[0]*nrows)
    st.session_state['df_obj'][f"var{ncols}"] = [0]

def solve_mip():
    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return
    infinity = solver.infinity()

    #generate vars from df
    all_vars = []
    for x in st.session_state.df_mip.columns[:len(st.session_state.df_mip.columns)]:
        #determine if variable is integer or continous
        if x in st.session_state.int_vars:
            all_vars.append(solver.IntVar(0,infinity,x))
        else:
            all_vars.append(solver.NumVar(0,infinity,x))

    #create constraints
    for index, row in st.session_state.df_mip.iterrows():
        #every entry except inequality and rhs
        if index < (len(row)-2):
            #multiply coefficients and vars
            constraint_expression = 0
            i = 0
            for coef in row[:-2]:
                constraint_expression += coef*all_vars[i]
                st.write(constraint_expression)
                i = i+1

            #add constraint with appropriate inequality and rhs to model
            if(row["inequality"] == ">="):
                solver.Add(constraint_expression>= row["RHS"])
            elif row["inequality"] == "<=":
                solver.Add(constraint_expression <= row["RHS"])
            elif row["inequality"] == ">":
                solver.Add(constraint_expression > row["RHS"])
            elif row["inequality"] == "<":
                solver.Add(constraint_expression <  row["RHS"])

    #create objective expression
    for index, row in st.session_state.df_obj.iterrows():
        if index < (len(row)-2):
            obj_expression = 0
            i = 0
            #multiply coefficients and variables
            for coef in row[:-2]:
                obj_expression += coef*all_vars[i]
                i = i+1

            #encode max min objective
            if(row["obj"] == "max"):
                solver.Maximize(obj_expression)
            else:
                solver.Minimize(obj_expression)

    #solve model
    status = solver.Solve()
    st.write(status)
    st.write(solver.Objective().Value())

def download_mip():
    #in memory location for excel file
    buffer = io.BytesIO()

    #used writer to write multiple df to same sheet
    with pd.ExcelWriter(buffer) as writer:
        st.session_state.df_obj.to_excel(writer, sheet_name="model", index=False)
        st.session_state.df_mip.to_excel(writer, sheet_name="model", index=False,startrow=4)
        writer.save()
        return buffer

def main():
    #initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': [10, 2, 3], 'var2': [4, 5, 6],'inequality':[">=","<=",">"],'RHS':[13,1000,1000]})
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({'var1': [1], 'var2': [45],"obj":"max"})

    col1,col2 = st.columns([6,1])
    with col1:
        #load obj grid
        load_obj_grid(st.session_state.df_obj)
        #load input grid
        load_constraints_grid(st.session_state.df_mip)

        #integrality constraints
        st.multiselect("Integer Variables",st.session_state.df_mip.columns[:len(st.session_state.df_mip) -1],key='int_vars')
        #allow for additional constraints
        st.button(label="\+ Constraint",on_click=add_row)
    with col2:
        #allow for additional variables
        st.button(label="\+ Variable",on_click=add_column)

    st.button(label="Solve",on_click=solve_mip)

    st.download_button(data=download_mip(), label="DL",file_name="test.xlsx" )

if __name__ == "__main__":
    main()




