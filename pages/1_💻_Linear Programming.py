import io

import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from ortools.linear_solver import pywraplp

def add_column():
    #get old data
    old_df = st.session_state['df_mip']

    #row and column lengths
    nrows = len(old_df)
    ncols = len(old_df.columns)

    #create new row with auto variable name
    st.session_state['df_mip'].insert(ncols-2,f"var{ncols-1}",['0']*nrows)
    st.session_state['df_obj'][f"var{ncols-1}"] = [0]

def solve_mip():
    #grab any modifications from data input
    st.session_state['df_mip'] = st.session_state['input_mip']
    st.session_state['df_obj'] = st.session_state['input_obj']

    st.session_state.solver_backend = None
    # choose solver based on context
    for x in st.session_state.df_mip.iloc[0]:
        #if integer or binary var ever observed, CP-SAT
        if (x == 'b') | (x == 'i'):
            st.session_state.solver_backend = "CP_SAT"

    #if no integer or binary observed, GLOP
    if st.session_state.solver_backend == None:
        st.session_state.solver_backend = 'GLOP'

    solver = pywraplp.Solver.CreateSolver(st.session_state.solver_backend)
    solver.SetTimeLimit(st.session_state['time_limit']*1000) #convert to ms

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
            if row["inequality"] == ">=":
                solver.Add(constraint_expression>= float(row["RHS"]),name=f"c{index}")
            elif row["inequality"] == "<=":
                solver.Add(constraint_expression <= float(row["RHS"]),name=f"c{index}")
            elif row["inequality"] == "==":
                solver.Add(constraint_expression == float(row["RHS"]),name=f"c{index}")
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
        st.session_state.solution_message = "No optimal solution found! "
        if status == solver.FEASIBLE:
            st.session_state['solution_message'] += "A potentially suboptimal solution was found. "
            solution_printer(solver=solver)
        elif status == solver.INFEASIBLE:
            st.session_state['solution_message'] += "The model is infeasible. "
            st.session_state['last_solution'] = pd.DataFrame()
        #elif status == solver.UNKNOWN:
        #    st.session_state['solution_message'] += "The model is status UNKNOWN. "
        #    st.session_state['last_solution'] = pd.DataFrame()
        elif status == solver.MODEL_INVALID:
            st.session_state['solution_message'] += "The model formulation did not pass the validation step. "
            st.session_state['last_solution'] = pd.DataFrame()
    elif status == solver.OPTIMAL:
        st.session_state['solution_message'] = f"An optimal solution was found in {solver.wall_time()/1000.0} s."
        solution_printer(solver=solver)

def solution_printer(solver):
    #dataframe to hold solution
    df_sol = pd.DataFrame()
    df_sol["obj"] = pd.Series(solver.Objective().Value())
    for x in solver.variables():
        if (x.name() != "inequality") & (x.name() != "RHS"):
            df_sol[x.name()] = pd.Series(x.SolutionValue())
    st.session_state['last_solution'] = df_sol

    activities = solver.ComputeConstraintActivities()
    o = [{'Name':c.name(), 'Shadow Price':c.dual_value(), 'Slack': c.ub() - activities[i]} for i, c in enumerate(solver.constraints())]
    st.session_state["sensitivity_analysis"] = pd.DataFrame(o)

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
        if st.session_state.solver_backend == 'GLOP':
            st.session_state.sensitivity_analysis.to_excel(writer,sheet_name="sensitivity",index=False,engine='xlsxwriter')

            #if a 2-var continous problem, save graphical solution to worksheet
            if two_var_graphical_solution() is not None:
                pd.DataFrame().to_excel(writer, sheet_name="graphical",index=False,engine='xlsxwriter')
                two_var_graphical_solution()
                plt.savefig("images/graphical.png")
                #writer.Workbook.add_worksheet('graphical')
                writer.sheets['graphical'].insert_image('A1',"images/graphical.png")
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

def two_var_graphical_solution():
    #set color scheme
    color_defaults = {
        'infeasible':'white',
        'feasible': 'lightgreen',
        'contour': 'darkgreen',
        'gradient':'blue'
    }

    #graphical representation of 2-var
    #https://stackoverflow.com/questions/36470343/how-to-draw-a-line-with-matplotlib#:~:text=x1%20are%20the%20x%20coordinates%20of%20the%20points,y1%2C%20x2%2C%20y2%2C%20marker%20%3D%20%27o%27%29%20plt.show%20%28%29

    #if the problem instance is 2-var
    if len(st.session_state["df_mip"].columns) - 2 == 2:
        df = st.session_state["df_mip"]

        #if continuous vars and no == constraints contained in formulation
        #TODO: Support for == constraints
        if (df[df.columns[0]][0] == 'c') & (df[df.columns[1]][0] == 'c') & ~('==' in df[df.columns[-2]].tolist()) :
            fig, ax = plt.subplots()

            #store constraint x and y intercepts for later figure scaling
            x_intercepts = []
            y_intercepts = []

            #for every row in df that represents a constraint
            for i in range(1,len(df)):
                #try to produce x and y intercepts of constraints at equality
                try:
                    ci_var1,ci_var2 = [float(df[df.columns[-1]][i])/float(df[df.columns[0]][i]),0], \
                                      [0,float(df[df.columns[-1]][i])/float(df[df.columns[1]][i])]
                    ax.plot(ci_var1,ci_var2,marker='o')

                    #handle constraint shading, inequalities are flipped because we are shading the infeasible region (easier)
                    if df[df.columns[-2]][i] == ">=":
                        ax.fill_between(ci_var1,ci_var2,color=color_defaults['infeasible'])
                    elif df[df.columns[-2]][i] == "<=":
                        ax.fill_between(ci_var1,ci_var2,1000,color= color_defaults['infeasible'],ec='none')
                        ax.fill_betweenx([0,1000],ci_var1[0]-0.00567,10000,color= color_defaults['infeasible'],ec='none')

                    x_intercepts.append(ci_var1[0])
                    y_intercepts.append(ci_var2[1])
                #vertical/horizontal line constraint catch
                except ZeroDivisionError:
                    #if a vertical line constraint
                    if float(df[df.columns[1]][i]) == 0:
                        ax.axvline(x=float(df[df.columns[-1]][i]),ymin=0,ymax=100,color=next(ax._get_lines.prop_cycler)['color'])

                        if df[df.columns[-2]][i] == "<=":
                            ax.fill_betweenx([0,1000],float(df[df.columns[-1]][i]),1000,color= color_defaults['infeasible'])
                        elif df[df.columns[-2]][i] == ">=":
                            ax.fill_betweenx([0,1000],0,float(df[df.columns[-1]][i]),color= color_defaults['infeasible'])
                        x_intercepts.append(float(df[df.columns[-1]][i]))

                    #if horizontal line constraint
                    elif float(df[df.columns[0]][i]) == 0:
                        ax.axhline(y=float(df[df.columns[-1]][i]),xmin=0,xmax=100,color=next(ax._get_lines.prop_cycler)['color'])

                        if df[df.columns[-2]][i] == "<=":
                            ax.fill_between([0,1000],float(df[df.columns[-1]][i]),1000,color= color_defaults['infeasible'])
                        elif df[df.columns[-2]][i] == ">=":
                            ax.fill_between([0,1000],0,float(df[df.columns[-1]][i]),color= color_defaults['infeasible'])
                        y_intercepts.append(float(df[df.columns[-1]][i]))

            #add gradient
            df_obj = st.session_state["df_obj"]
            #contour slope
            slope_contour = -float(df_obj[df_obj.columns[1]][0])/float(df_obj[df_obj.columns[2]][0])

            #scale the gradient to avg of x and y max
            length_gradient = (max(x_intercepts) + max(y_intercepts) )/3#TODO: this is a decent est, needs to be revisited

            #add gradient
            #if statements correct for direction of improvement
            if df_obj["obj"][0] == 'max':
                plt.arrow(0,0,length_gradient,length_gradient*(-1.0/slope_contour),width=0.7,length_includes_head=True,color=color_defaults['gradient'])
            elif df_obj["obj"][0] == 'min':
                plt.arrow(length_gradient,length_gradient*(-1.0/slope_contour),-length_gradient,-length_gradient*(-1.0/slope_contour),width=0.7,length_includes_head=True,color=color_defaults['gradient'])

            #contour lines with y intercept at x intercept of constraints
            for intercept in x_intercepts:
                x = [0,-intercept/slope_contour]
                y = [x_val*slope_contour + intercept for x_val in x]
                ax.plot(x,y,dashes=(6,2),color=color_defaults['contour'])

            #set axis
            plt.axis([0,max(x_intercepts),0,max(y_intercepts)])

            #set background
            ax.set_facecolor(color_defaults['feasible'])
            #return figure for continous, 2-var example
            return fig
        else:
            #return no figure
            return None
def main():
    st.set_page_config(layout="wide")

    st.title("Linear Programming")
    #initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': pd.Series(['c',2.0, 1.0, 1.0],dtype='string'), 'var2': pd.Series(['c',1.0, 1.0, 0.0],dtype='string'),'inequality':["","<=","<=","<="],'RHS':pd.Series(['',100.0,80.0,40.0])})
        st.session_state['input_mip'] = pd.DataFrame()
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({"obj":"max",'var1': pd.Series([3.0],dtype='double'), 'var2':pd.Series([2.0],dtype='double')})
        st.session_state['input_obj'] = pd.DataFrame()
    if 'solver_backend' not in st.session_state:
        st.session_state.solver_backend = None
    #setup sidebar
    #allow for File I/O
    with st.sidebar:
        st.header("Model Input/Output")
        st.file_uploader(label="Upload an Excel Model",type='.xlsx',key="model_up",on_change=upload_mip,help="Import xlsx file containing model formulation")
        st.download_button(data=download_mip(), label="Download Current Model",file_name="model.xlsx",help="Downloads formulation in xlsx format" )
        if 'last_solution' in st.session_state:
            st.download_button(data=download_sol(), label="Download Model + Solution",file_name="model-solution.xlsx",help="Downloads formulation, solution, and sensitivity report in xlsx format")
        st.header("Settings")
        st.checkbox("Do not render model",help="Improves performance for large models by hiding the editable dataframe. ",key="hide_model")
        st.checkbox("Do not render solution",help="Improves performance for large solutions by hiding output dataframe",key="hide_solution")
        st.number_input("Time Limit (s)",value=60, key="time_limit")
    #main page
    col1,col2 = st.columns([6,1])
    with col1:
        if st.session_state["hide_model"] is False:
            #load obj grid, save input
            st.session_state['input_obj'] = st.experimental_data_editor(st.session_state["df_obj"],num_rows="dynamic")
            #load input grid, save input
            st.session_state['input_mip'] = st.experimental_data_editor(st.session_state["df_mip"],num_rows="dynamic")

    with col2:
        #adding white space. TODO: More elegant solution?
        for x in range(0,6):
            st.write("")

        #allow for additional variables
        st.button(label="Add Variable",on_click=add_column,help="Creates a new variable column")

    st.button(label="Solve",on_click=solve_mip,help="Solves the model")

    if st.session_state['hide_solution'] is False:
        if 'last_solution' in st.session_state:
            st.write(st.session_state['solution_message'])
            st.write(st.session_state['last_solution'])
        if st.session_state['solver_backend'] is 'GLOP':
            if 'sensitivity_analysis' in st.session_state:
                st.write("The sensitivity of the constraint set is as follows: ")
                st.write(st.session_state['sensitivity_analysis'])

    #determine if a graphical solution can be generated
    figure = two_var_graphical_solution()

    if st.session_state['hide_solution'] is False:
        #if a graphical solution generated, display it
        if figure is not None:
            st.write("Graphical Representation")
            col1,col2 = st.columns([3,2])
            col1.pyplot(figure)


if __name__ == "__main__":
    main()




