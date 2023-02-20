import io

import numpy as np
import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from ortools.linear_solver import pywraplp
def load_obj_grid(df):
    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df,editable=True)
    builder.configure_column("obj", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["min","max"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    st.session_state['aggrid_obj'] = AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True,height=65, enable_enterprise_modules=False)

def load_constraints_grid(df):
    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df, editable=True)
    builder.configure_column("inequality", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["<=",">=","=="]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    st.session_state['aggrid_mip'] = AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True, enable_enterprise_modules=False,reload_data=False,update_mode=GridUpdateMode.GRID_CHANGED)

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

    # Create the mip solver with the SCIP backend.
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return
    infinity = solver.infinity()

    #generate vars from df
    all_vars = []

    #index and list to name or-tools variables appropriately
    colnames = st.session_state.df_mip.columns
    col_ind = 0
    for x in st.session_state.df_mip.iloc[0]:
        #determine if variable is integer or continous
        if str(x)  == 'i':
            all_vars.append(solver.IntVar(0,infinity,colnames[col_ind]))
        elif str(x) == 'c':
            all_vars.append(solver.NumVar(0,infinity,colnames[col_ind]))
        elif str(x) == 'b':
            all_vars.append(solver.IntVar(0,1,colnames[col_ind]))
        col_ind += 1

    #create constraints
    for index, row in st.session_state.df_mip.iterrows():
        #every entry except i/c
        if index >= 1:
            #multiply coefficients and vars
            constraint_expression = 0
            i = 0
            #every entry except rhs
            for coef in row[:-2]:
                constraint_expression += float(coef)*all_vars[i]
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

    #report results and save message to session state
    if status != solver.OPTIMAL:
        st.session_state.solution_message = "No optimal solution found!"
        if status == solver.FEASIBLE:
            st.session_state['solution_message'] += "A potentially suboptimal solution was found"
            solution_printer(solver=solver)
        else:
            st.session_state['solution_message'] += "The solver could not solve the problem. "
            st.session_state['last_solution'] = pd.DataFrame()
    elif status == solver.OPTIMAL:
        st.session_state['solution_message'] = f"An optimal solution was found in {solver.wall_time()/1000.0} s."
        solution_printer(solver=solver)

def solution_printer(solver):
    #GLOP only
    #st.write(solver.constraints()[2].DualValue())
    #dataframe to hold solution
    df_sol = pd.DataFrame()
    df_sol["obj"] = pd.Series(solver.Objective().Value())
    for x in solver.variables():
        if (x.name() != "inequality") & (x.name() != "RHS"):
            df_sol[x.name()] = pd.Series(x.SolutionValue())
    st.session_state['last_solution'] = df_sol
def download_mip():
    #in memory location for excel file
    buffer = io.BytesIO()

    #used writer to write multiple df to same sheet
    with pd.ExcelWriter(buffer) as writer:
        st.session_state.df_obj.to_excel(writer, sheet_name="model", index=False, engine='xlsxwriter')
        st.session_state.df_mip.to_excel(writer, sheet_name="model", index=False,startrow=4, engine='xlsxwriter')
        return buffer

def download_sol():
    #in memory location for excel file
    buffer = io.BytesIO()

    #used writer to write multiple df to same sheet
    with pd.ExcelWriter(buffer) as writer:
        st.session_state.df_obj.to_excel(writer, sheet_name="model", index=False, engine='xlsxwriter')
        st.session_state.df_mip.to_excel(writer, sheet_name="model", index=False,startrow=4, engine='xlsxwriter')
        st.session_state.last_solution.to_excel(writer, sheet_name="solution", index=False, engine='xlsxwriter')
        return buffer
def upload_mip():
    #get file from uploader
    if st.session_state.model_up is None:
        #do not access buffer if this callback is the result of user deleting upload file
        return
    else:
        file_input = st.session_state.model_up
        file_input_df = pd.read_excel(file_input, engine='openpyxl')

    #get the objective table and convert to dataframe
    df_obj = file_input_df.drop([x for x in range(1, len(file_input_df))])
    df_obj.pop(df_obj.columns.values[-1])

    #get the constraint table and convert to dataframe
    df_mip = file_input_df.drop(x for x in range(0,3))
    df_mip.reset_index(drop=True, inplace=True)
    df_mip.columns = df_mip.iloc[0]
    df_mip = df_mip.drop(0)
    #make sure index starts with 0
    df_mip.reset_index(drop=True, inplace=True)

    #reset project data
    st.session_state.df_mip = df_mip
    st.session_state.df_obj = df_obj
def main():
    st.set_page_config(layout="wide")

    st.title("Linear Programming")
    #initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': pd.Series(['c',2.0, 1.0, 1.0]), 'var2': pd.Series(['c',1.0, 1.0, 0.0]),'inequality':["","<=","<=","<="],'RHS':pd.Series(['',100.0,80.0,40.0])})
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({"obj":"max",'var1': pd.Series([3.0],dtype='double'), 'var2':pd.Series([2.0],dtype='double')})

    col1,col2 = st.columns([6,1])
    with col1:
        #load obj grid
        load_obj_grid(st.session_state.df_obj)
        #load input grid
        load_constraints_grid(st.session_state.df_mip)

        #allow for additional constraints
        st.button(label="\+ Constraint",on_click=add_row)

    with col2:
        #adding white space. TODO: More elegant solution?
        for x in range(0,6):
            st.write("")

        #allow for additional variables
        st.button(label="\+ Variable",on_click=add_column)

    st.button(label="Solve",on_click=solve_mip)


    #graphical representation
    # plot
    #https://stackoverflow.com/questions/36470343/how-to-draw-a-line-with-matplotlib#:~:text=x1%20are%20the%20x%20coordinates%20of%20the%20points,y1%2C%20x2%2C%20y2%2C%20marker%20%3D%20%27o%27%29%20plt.show%20%28%29
    # 2 var example
    if len(st.session_state["df_mip"].columns) -2 == 2:
        df = st.session_state["df_mip"]
        fig, ax = plt.subplots()

        x_intercepts = []
        for i in range(1,len(df)):
            st.write("iter")
            ci_var1,ci_var2 = [np.divide(float(df[df.columns[-1]][i]),float(df[df.columns[0]][i])),0], \
                              [0,np.divide(float(df[df.columns[-1]][i]),float(df[df.columns[1]][i]))]
            ax.plot(ci_var1,ci_var2,marker='o')
            ax.fill_between(ci_var1,ci_var2,alpha=0.5)
            x_intercepts.append(ci_var1[0])
        #c1_var1,c1_var2 = [float(df[df.columns[-1]][1])/float(df[df.columns[0]][1]),0],\
        #                  [0,float(df[df.columns[-1]][1])/float(df[df.columns[1]][1])]
        #c2_var1,c2_var2 = [float(df[df.columns[-1]][2])/float(df[df.columns[0]][2]),0], \
         #                 [0,float(df[df.columns[-1]][2])/float(df[df.columns[1]][2])]
        #ax.plot(c1_var1,c1_var2,c2_var1,c2_var2,marker='o')

        #shade feasible region on per constraint basis
        #ax.fill_between(c1_var1,c1_var2,alpha=0.5) #alpha controls transparency
        #ax.fill_between(c2_var1,c2_var2,alpha=0.5)

        #add gradient
        df_obj = st.session_state["df_obj"]
        #contour slope
        slope_contour = -float(df_obj[df_obj.columns[1]][0])/float(df_obj[df_obj.columns[2]][0])

        length_gradient = float(df[df.columns[-1]][2])/float(df[df.columns[1]][2])*0.7 #TODO: this is a decent est, needs to be revisited

        #add gradient
        if df_obj["obj"][0] == 'max':
            plt.arrow(0,0,length_gradient,length_gradient*(-1.0/slope_contour),width=0.7)
        elif df_obj["obj"][0] == 'min':
            plt.arrow(length_gradient,length_gradient*(-1.0/slope_contour),-length_gradient,-length_gradient*(-1.0/slope_contour),width=0.7)
        #contour lines with y intercept at x intercept of constraints
        for intercept in x_intercepts:
            x = [0,-intercept/slope_contour]
            y = [x_val*slope_contour + intercept for x_val in x]
            ax.plot(x,y,dashes=(6,2),color="green")


        st.pyplot(fig)




    if 'last_solution' in st.session_state:
        st.write(st.session_state['solution_message'])
        st.write(st.session_state['last_solution'])
        st.download_button(data=download_sol(), label="Download Model + Solution",file_name="model-solution.xlsx")

    #allow for File I/O
    with st.sidebar:
        st.download_button(data=download_mip(), label="Download Model",file_name="model.xlsx" )
        st.file_uploader(label="Upload Model",type='.xlsx',key="model_up",on_change=upload_mip)

if __name__ == "__main__":
    main()




