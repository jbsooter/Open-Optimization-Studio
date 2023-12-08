import re

import numpy as np
import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from ortools.linear_solver import pywraplp
from ortools.linear_solver.python import model_builder as mb
from scipy.spatial import ConvexHull

from streamlit_ace import st_ace

from utilities import config


def add_column():
    # get old data
    old_df = st.session_state['df_mip']

    # row and column lengths
    nrows = len(old_df)
    ncols = len(old_df.columns)

    # create new row with auto variable name
    st.session_state['df_mip'].insert(
        ncols - 2, f"var{ncols-1}", ['0'] * nrows)
    st.session_state['df_obj'][f"var{ncols-1}"] = [0]

def solve_mip():
    # grab any modifications from data input
    st.session_state['df_mip'] = st.session_state['input_mip']
    st.session_state['df_obj'] = st.session_state['input_obj']

    st.session_state.solver_backend = None
    # choose solver based on context
    for x in st.session_state.df_mip.iloc[0]:
        # if integer or binary var ever observed, CP-SAT
        if (x == 'b') | (x == 'i'):
            st.session_state.solver_backend = config.solver_backend['mip']
            st.session_state.lp_type = 'mip'

    # if no integer or binary observed, use linear solver
    if st.session_state.solver_backend is None:
        st.session_state.solver_backend = config.solver_backend['linear']
        st.session_state.lp_type = 'lp'

    solver = pywraplp.Solver.CreateSolver(st.session_state.solver_backend)
    solver.SetTimeLimit(st.session_state['time_limit'] * 1000)  # convert to ms

    if not solver:
        return
    infinity = solver.infinity()

    # generate vars from df
    all_vars = []

    # index and list to name or-tools variables appropriately
    colnames = st.session_state.df_mip.columns
    col_ind = 0
    for x in st.session_state.df_mip.iloc[0]:
        # determine if variable is integer or continous
        if str(x) == 'i':
            all_vars.append(solver.IntVar(0, infinity, colnames[col_ind]))
        elif str(x) == 'c':
            all_vars.append(solver.NumVar(0, infinity, colnames[col_ind]))
        elif str(x) == 'b':
            all_vars.append(solver.IntVar(0, 1, colnames[col_ind]))
        col_ind += 1

    # create constraints
    for index, row in st.session_state.df_mip.iterrows():
        # every entry except i/c
        if index >= 1:
            # multiply coefficients and vars
            constraint_expression = 0
            i = 0
            # every entry except rhs
            for coef in row[:-2]:
                constraint_expression += float(coef) * all_vars[i]
                i = i + 1

            # add constraint with appropriate inequality and rhs to model
            if row["inequality"] == ">=":
                solver.Add(
                    constraint_expression >= float(
                        row["RHS"]), name=f"c{index}")
            elif row["inequality"] == "<=":
                solver.Add(
                    constraint_expression <= float(
                        row["RHS"]), name=f"c{index}")
            elif row["inequality"] == "==":
                solver.Add(
                    constraint_expression == float(
                        row["RHS"]), name=f"c{index}")
    # create objective expression
    for index, row in st.session_state.df_obj.iterrows():
        if index < (len(row) - 2):
            obj_expression = 0
            i = 0
            # multiply coefficients and variables
            for coef in row[1:]:
                obj_expression += float(coef) * all_vars[i]
                i = i + 1

            # encode max min objective
            if (row["obj"] == "max"):
                solver.Maximize(obj_expression)
            else:
                solver.Minimize(obj_expression)

    # solve model
    status = solver.Solve()

    # report results and save message to session state
    if status != solver.OPTIMAL:
        st.session_state.solution_message = "No optimal solution found! "
        if status == solver.FEASIBLE:
            st.session_state['solution_message'] += "A potentially suboptimal solution was found. "
            solution_printer(solver=solver)
        elif status == solver.INFEASIBLE:
            st.session_state['solution_message'] += "The model is infeasible. "
            st.session_state['last_solution'] = pd.DataFrame()
        # elif status == solver.UNKNOWN:
        #    st.session_state['solution_message'] += "The model is status UNKNOWN. "
        #    st.session_state['last_solution'] = pd.DataFrame()
        elif status == solver.MODEL_INVALID:
            st.session_state['solution_message'] += "The model formulation did not pass the validation step. "
            st.session_state['last_solution'] = pd.DataFrame()
    elif status == solver.OPTIMAL:
        st.session_state[
            'solution_message'] = f"An optimal solution was found in {solver.wall_time()/1000.0} s."
        solution_printer(solver=solver)


def solution_printer(solver):
    # dataframe to hold solution
    df_sol = pd.DataFrame()
    df_sol["obj"] = pd.Series(solver.Objective().Value())
    for x in solver.variables():
        if (x.name() != "inequality") & (x.name() != "RHS"):
            df_sol[x.name()] = pd.Series(x.SolutionValue())
    st.session_state['last_solution'] = df_sol

    activities = solver.ComputeConstraintActivities()
    o = [{'Name': c.name(),
          'Shadow Price': c.dual_value(),
          'Slack': c.ub() - activities[i]} for i,
         c in enumerate(solver.constraints())]
    st.session_state["sensitivity_analysis"] = pd.DataFrame(o)


class Arrow3D:
    pass


def three_var_graphical_solution():
    #https://demonstrations.wolfram.com/GraphicalLinearProgrammingForThreeVariables/
    if len(st.session_state["df_mip"].columns) - 2 == 3:
        #get constraints
        df = st.session_state["df_mip"]
        #assign coeffs and rhs to column variables
        a = np.array(df["var1"][1:].astype(float))
        b = np.array(df["var2"][1:].astype(float))
        c = np.array(df["var3"][1:].astype(float))
        d = np.array(df["RHS"][1:].astype(float))

        #create matplotlib objects
        fig = plt.figure()
        ax = fig.add_subplot(111,projection='3d')

        #find zeros (vertices)
        vert = []
        for i in range(0,len(a)):
            vert.append([min(100000,d[i]/a[i]),0,0])
            vert.append([0,min(100000,d[i]/b[i]),0])
            vert.append([0,0,min(100000,d[i]/c[i])])

        vert.append([0,0,0])

        hull = ConvexHull(vert)
        shape = Poly3DCollection([hull.points[facet] for facet in hull.simplices],edgecolors='red')
        ax.add_collection3d(shape)
        #label axes
        ax.set_xlabel("X")
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')


        #https://matplotlib.org/stable/api/toolkits/mplot3d/view_angles.html
        #ax.view_init(45,45,0)
        #find limits assuming all decision variables > 0
        x_max = [x[0] for x in vert]
        x_max = max(x_max)

        y_max = [x[1] for x in vert]
        y_max = max(y_max)

        z_max = [x[2] for x in vert]
        z_max = max(z_max)

        #set limits
        ax.set_xlim(x_max,0)
        ax.set_ylim(0,y_max)
        ax.set_zlim3d(0,z_max)

        #plot
        return fig
    else:
        return None

def two_var_graphical_solution():
    # set color scheme
    color_defaults = config.two_var_color_defaults

    # graphical representation of 2-var
    # https://stackoverflow.com/questions/36470343/how-to-draw-a-line-with-matplotlib#:~:text=x1%20are%20the%20x%20coordinates%20of%20the%20points,y1%2C%20x2%2C%20y2%2C%20marker%20%3D%20%27o%27%29%20plt.show%20%28%29

    # if the problem instance is 2-var
    if len(st.session_state["df_mip"].columns) - 2 == 2:
        df = st.session_state["df_mip"]

        # if continuous vars and no == constraints contained in formulation
        # TODO: Support for == constraints
        if (df[df.columns[0]][0] == 'c') & (df[df.columns[1]][0]
                                            == 'c') & ~('==' in df[df.columns[-2]].tolist()):
            fig, ax = plt.subplots()

            # store constraint x and y intercepts for later figure scaling
            x_intercepts = []
            y_intercepts = []

            # for every row in df that represents a constraint
            for i in range(1, len(df)):
                # produce x and y intercepts of constraints at equality
                try:
                    ci_var1, ci_var2 = [float(df[df.columns[-1]][i]) / float(df[df.columns[0]][i]), 0], \
                        [0, float(df[df.columns[-1]][i]) / float(df[df.columns[1]][i])]
                    ax.plot(ci_var1, ci_var2, marker='o')

                    # handle constraint shading, inequalities are flipped
                    # because we are shading the infeasible region (easier)
                    if df[df.columns[-2]][i] == ">=":
                        ax.fill_between(
                            ci_var1, ci_var2, color=color_defaults['infeasible'])
                    elif df[df.columns[-2]][i] == "<=":
                        ax.fill_between(
                            ci_var1,
                            ci_var2,
                            1000,
                            color=color_defaults['infeasible'],
                            ec='none')
                        ax.fill_betweenx([0,
                                          1000],
                                         ci_var1[0] - 0.00567,
                                         10000,
                                         color=color_defaults['infeasible'],
                                         ec='none')

                    x_intercepts.append(ci_var1[0])
                    y_intercepts.append(ci_var2[1])
                # vertical/horizontal line constraint catch
                except ZeroDivisionError:
                    # if a vertical line constraint
                    if float(df[df.columns[1]][i]) == 0:
                        ax.axvline(x=float(df[df.columns[-1]][i]),
                                   ymin=0,
                                   ymax=100,
                                   color=next(ax._get_lines.prop_cycler)['color'])

                        if df[df.columns[-2]][i] == "<=":
                            ax.fill_betweenx([0, 1000], float(
                                df[df.columns[-1]][i]), 1000, color=color_defaults['infeasible'])
                        elif df[df.columns[-2]][i] == ">=":
                            ax.fill_betweenx([0, 1000], 0, float(
                                df[df.columns[-1]][i]), color=color_defaults['infeasible'])
                        x_intercepts.append(float(df[df.columns[-1]][i]))

                    # if horizontal line constraint
                    elif float(df[df.columns[0]][i]) == 0:
                        ax.axhline(y=float(df[df.columns[-1]][i]),
                                   xmin=0,
                                   xmax=100,
                                   color=next(ax._get_lines.prop_cycler)['color'])

                        if df[df.columns[-2]][i] == "<=":
                            ax.fill_between([0, 1000], float(
                                df[df.columns[-1]][i]), 1000, color=color_defaults['infeasible'])
                        elif df[df.columns[-2]][i] == ">=":
                            ax.fill_between([0, 1000], 0, float(
                                df[df.columns[-1]][i]), color=color_defaults['infeasible'])
                        y_intercepts.append(float(df[df.columns[-1]][i]))

            # add gradient
            df_obj = st.session_state["df_obj"]
            # contour slope
            slope_contour = - \
                float(df_obj[df_obj.columns[1]][0]) / float(df_obj[df_obj.columns[2]][0])

            # scale the gradient to avg of x and y max
            # TODO: this is a decent est, needs to be revisited
            length_gradient = (max(x_intercepts) + max(y_intercepts)) / 3

            # add gradient
            # if statements correct for direction of improvement
            if df_obj["obj"][0] == 'max':
                plt.arrow(0,
                          0,
                          length_gradient,
                          length_gradient * (-1.0 / slope_contour),
                          width=0.7,
                          length_includes_head=True,
                          color=color_defaults['gradient'])
            elif df_obj["obj"][0] == 'min':
                plt.arrow(length_gradient, length_gradient * (-1.0 / slope_contour), -length_gradient, -length_gradient *
                          (-1.0 / slope_contour), width=0.7, length_includes_head=True, color=color_defaults['gradient'])

            # contour lines with y intercept at x intercept of constraints
            for intercept in list(range(0,int(max(x_intercepts)),20)):
                x = [0, -intercept / slope_contour]
                y = [x_val * slope_contour + intercept for x_val in x]
                ax.plot(x, y, dashes=(6, 2), color=color_defaults['contour'])

            # set axis
            plt.axis([0, max(x_intercepts), 0, max(y_intercepts)])

            # set background
            ax.set_facecolor(color_defaults['feasible'])
            # return figure for continous, 2-var example
            return fig
        else:
            # return no figure
            return None

def solve_lp_file(lp_string):
    # https://github.com/google/or-tools/issues/523
    # https://web.mit.edu/lpsolve/doc/lp-format.htm

    #declare modelBuilder
    model = mb.ModelBuilder()

    #Pre-OR-Tools Clean.
    # 1. Removes // style comments.
    # Assumes lp_string coming in as single string
    # Split the input string by newline character
    lines = lp_string.split("\n")

    #remove comment from each line
    for i in range(len(lines)):
        if "//" in lines[i]:
            lines[i] = lines[i].split("//")[0]

    # rejoin strings to one and assign to lp_string
    lp_string = "\n".join(lines)

    #2. remove block comment \* *\
    lp_string= re.sub(r'/\*.*?\*/','',lp_string)

    #import LP format model from ace editor component
    model.import_from_lp_string(lp_string=lp_string)

    #verify that model imported successfully. If not, end method and show error message
    if model.num_variables == 0:
        st.error("LP Model Import Failed. Try Again. ")
        return

    #determine linear or mip and create ModelSolver
    solver = mb.ModelSolver(config.solver_backend['linear'])
    variables = [model.var_from_index(i) for i in range(model.num_variables)]
    for x in variables:
        if x.is_integral:
            solver = mb.ModelSolver(config.solver_backend['mip'])

    #pply tl
    solver.set_time_limit_in_seconds(st.session_state['time_limit'])
    # solve model
    status = solver.solve(model)

    # update solution status. TOD:ckean up
    st.session_state['solution_message'] = str(status)

    # convert soluiton to df
    # Create an empty dictionary to store the column names and values
    solution = {}

    # Add the objective value to the dictionary
    solution["obj"] = solver.objective_value

    # Loop through the variables and add their names and values to the dictionary
    variables = [model.var_from_index(i) for i in range(model.num_variables)]
    for x in variables:
        solution[x.name] = solver.value(x)

    st.session_state['lp_type'] = 'lp'
    for x in variables:
        if x.is_integral:
            st.session_state['lp_type'] = 'mip'
            st.session_state['sensitivity_analysis'] = None
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(solution, index=[0])

    #update solution session state
    st.session_state['last_solution'] = df

    if st.session_state['lp_type'] == 'lp':
        #todo produce this
        st.session_state["sensitivity_analysis"] = None

def clear_problem_ss():
    #reset to original values
    st.session_state['df_mip'] = pd.DataFrame({'var1': pd.Series(['c', 2.0, 1.0, 1.0], dtype='string'), 'var2': pd.Series(
        ['c', 1.0, 1.0, 0.0], dtype='string'), 'inequality': ["", "<=", "<=", "<="], 'RHS': pd.Series(['', 100.0, 80.0, 40.0],dtype='string')})
    st.session_state['input_mip'] = pd.DataFrame()
    st.session_state['df_obj'] = pd.DataFrame({"obj": "max", 'var1': pd.Series(
        [3.0], dtype='double'), 'var2': pd.Series([2.0], dtype='double')})
    st.session_state['input_obj'] = pd.DataFrame()

    st.session_state['last_solution'] = None

def main():
    st.set_page_config(layout="wide")

    st.subheader("Linear Programming")

    # initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': pd.Series(['c', 2.0, 1.0, 1.0], dtype='string'), 'var2': pd.Series(
            ['c', 1.0, 1.0, 0.0], dtype='string'), 'inequality': ["", "<=", "<=", "<="], 'RHS': pd.Series(['', 100.0, 80.0, 40.0],dtype='string')})
        st.session_state['input_mip'] = pd.DataFrame()
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({"obj": "max", 'var1': pd.Series(
            [3.0], dtype='double'), 'var2': pd.Series([2.0], dtype='double')})
        st.session_state['input_obj'] = pd.DataFrame()
    if 'solver_backend' not in st.session_state:
        st.session_state.solver_backend = None
    if 'lp_type' not in st.session_state:
        st.session_state.lp_type = None
    if 'last_solution' not in st.session_state:
        st.session_state['last_solution'] = None


    # setup sidebar
    # allow for File I/O
    with st.sidebar:
        st.selectbox(label="Mode",options=['LP','Tableau'],index=1,key='model_mode_lp',on_change=clear_problem_ss)

        st.header("Settings")
        st.number_input("Time Limit (s)", value=60, key="time_limit")
        st.write("[Docs](https://jbsooter.github.io/Open-Optimization-Studio/Linear%20Programming)")
        #todo add to others

    #lp mit mode
    if st.session_state['model_mode_lp'] == 'LP':
        lp_editor= st_ace("""max: 3x + 2y;

        c1: 2x + y <= 100;

        c2: x + y <= 80;

        c3: x  <= 40;

        x >= 0;

        y >= 0;""",
                          language='text'
                          ,auto_update=True)



        st.button(label="Solve model",key="solvelpmodel",on_click=solve_lp_file,args=[''.join(lp_editor)])
    elif st.session_state["model_mode_lp"] == 'Tableau':
        # main page
        col1, col2 = st.columns([2,1])
        with col1:
            # load obj grid, save input
            st.session_state['input_obj'] = st.data_editor(
                st.session_state["df_obj"], num_rows="dynamic")
            # load input grid, save input
            st.session_state['input_mip'] = st.data_editor(
                st.session_state["df_mip"], num_rows="dynamic")

        with col2:
            # allow for additional variables
            st.button(
                label="Add Variable",
                on_click=add_column,
                help="Creates a new variable column")

        st.button(label="Solve", on_click=solve_mip, help="Solves the model")


    if st.session_state['last_solution'] is not None:
        col1, col2 = st.columns([1,2])
        col1.write(st.session_state['solution_message'])
        col1.write(st.session_state['last_solution'])


        if st.session_state['lp_type'] == 'lp':
            if 'sensitivity_analysis' in st.session_state:
                col1.write("The sensitivity of the constraint set is as follows: ")
                col1.write(st.session_state['sensitivity_analysis'])

        #TODO: Support Graphical with LP Format
        if st.session_state['model_mode_lp'] == 'LP':
            figure = None
        else:
            # determine if a graphical solution can be generated
            figure = two_var_graphical_solution()

            if figure is None:
                figure = three_var_graphical_solution()


        # if a graphical solution generated, display it
        if figure is not None:
            col2.write("Graphical Representation")

            col2.pyplot(figure)



if __name__ == "__main__":
    main()
