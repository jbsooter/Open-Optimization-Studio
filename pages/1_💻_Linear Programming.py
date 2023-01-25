import io
import streamlit as st
import pandas as pd
from numpy import double
from st_aggrid import AgGrid, GridOptionsBuilder
from ortools.linear_solver import pywraplp
from openpyxl import load_workbook
def load_obj_grid(df):
    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df,editable=True)
    builder.configure_column("obj", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["min","max"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    st.session_state['aggrid_obj'] = AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True,height=65)

def load_constraints_grid(df):

    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df, editable=True)
    builder.configure_column("inequality", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["<=",">=","=","<",">"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    st.session_state['aggrid_mip'] = AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True)

def add_row():
    st.session_state['df_mip'] = st.session_state['aggrid_mip']['data']
    #get existing
    old_df = st.session_state['df_mip']

    #create dataframe representing new row
    new_row = pd.DataFrame()
    for col in old_df.columns:
        new_row[col] = [0]

    #create and save new, combined dataframe
    st.session_state['df_mip'] = pd.concat([old_df, new_row])

def add_column():
    st.session_state['df_mip'] = st.session_state['aggrid_mip']['data']
    #get old data
    old_df = st.session_state['df_mip']

    #row and column lengths
    nrows = len(old_df)
    ncols = len(old_df.columns)

    #create new row with auto variable name
    st.session_state['df_mip'].insert(ncols-2,f"var{ncols-1}",[0]*nrows)
    st.session_state['df_obj'][f"var{ncols-1}"] = [0]

def solve_mip():
    st.session_state['df_mip'] = st.session_state['aggrid_mip']['data']
    st.session_state['df_obj'] = st.session_state['aggrid_obj']['data']
    st.write(st.session_state['df_mip'])
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
                constraint_expression += float(coef)*all_vars[i]
                st.write(constraint_expression)
                i = i+1

            #add constraint with appropriate inequality and rhs to model
            if(row["inequality"] == ">="):
                solver.Add(constraint_expression>= float(row["RHS"]))
            elif row["inequality"] == "<=":
                solver.Add(constraint_expression <= float(row["RHS"]))
            elif row["inequality"] == ">":
                solver.Add(constraint_expression > float(row["RHS"]))
            elif row["inequality"] == "<":
                solver.Add(constraint_expression <  float(row["RHS"]))

    #create objective expression
    for index, row in st.session_state.df_obj.iterrows():
        if index < (len(row)-2):
            obj_expression = 0
            i = 0
            #multiply coefficients and variables
            for coef in row[1:]:
                obj_expression += float(coef)*all_vars[i]
                i = i+1

            #encode max min objective
            if(row["obj"] == "max"):
                solver.Maximize(obj_expression)
            else:
                solver.Minimize(obj_expression)

    #solve model
    status = solver.Solve()

    #report results
    if status != solver.OPTIMAL:
        st.write("No optimal solution found!")
        if status == solver.FEASIBLE:
            st.write("A potentially suboptimal solution was found")
            solution_printer(solver=solver)
        else:
            st.write("The solver could not solve the problem. ")
    elif status == solver.OPTIMAL:
        st.write(f"An optimal solution was found in {solver.wall_time()/1000.0} s.")
        solution_printer(solver=solver)


def solution_printer(solver):
    st.write(f"Objective Value: {solver.Objective().Value()}")
    for x in solver.variables():
        if (x.name() != "inequality") & (x.name() != "RHS"):
            st.write(x.name() + " " + str(x.SolutionValue()))
    #st.write(solver.variables()[0].SolutionValue())
def download_mip():
    #in memory location for excel file
    buffer = io.BytesIO()

    #used writer to write multiple df to same sheet
    with pd.ExcelWriter(buffer) as writer:
        st.session_state.df_obj.to_excel(writer, sheet_name="model", index=False)
        st.session_state.df_mip.to_excel(writer, sheet_name="model", index=False,startrow=4)
        writer.save()
        return buffer

def upload_mip():
    #get file from uploader TODO error on reset
    file_input = st.session_state.model_up
    file_input_df = pd.read_excel(file_input)

    #get the objective table and convert to dataframe
    df_obj = file_input_df.drop([x for x in range(1, len(file_input_df))])
    df_obj.pop(df_obj.columns.values[-1])

    #get the constraint table and convert to dataframe
    df_mip = file_input_df.drop(x for x in range(0,3))
    df_mip.reset_index(drop=True, inplace=True)
    df_mip.columns = df_mip.iloc[0]
    df_mip = df_mip.drop(0)

    #reset project data
    st.session_state.df_mip = df_mip
    st.session_state.df_obj = df_obj
def main():
    #initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': pd.Series([10.0, 2.0, 3.0], dtype='double'), 'var2': pd.Series([4.0, 5.0, 6.0],dtype='double'),'inequality':[">=","<=",">"],'RHS':pd.Series([13.0,1000.0,1000.0],dtype='double')})
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({"obj":"max",'var1': pd.Series([1.0],dtype='double'), 'var2':pd.Series([45.0],dtype='double')})

    col1,col2 = st.columns([6,1])
    with col1:
        #load obj grid
        load_obj_grid(st.session_state.df_obj)
        #load input grid
        load_constraints_grid(st.session_state.df_mip)

        #allow for additional constraints
        st.button(label="\+ Constraint",on_click=add_row)
        #integrality constraints
        st.multiselect("Integer Variables",st.session_state.df_mip.columns[:len(st.session_state.df_mip) -1],key='int_vars')

    with col2:
        #adding white space. More elegant solution?
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")

        #allow for additional variables
        st.button(label="\+ Variable",on_click=add_column)

    st.button(label="Solve",on_click=solve_mip)

    #allow for File I/O
    with st.sidebar:
        st.download_button(data=download_mip(), label="Download Model",file_name="model.xlsx" )
        st.file_uploader(label="Upload Model",type='.xlsx',key="model_up",on_change=upload_mip)

if __name__ == "__main__":
    main()




