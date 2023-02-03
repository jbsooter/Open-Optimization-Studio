from _ast import List
from collections.abc import Iterable

import pandas as pd
from ortools.linear_solver import pywraplp


def parse_text_to_model(text):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return
    infinity = solver.infinity()

    #split string at newlines
    model_lines = text.splitlines()

    #dicts to store decision variables and coefficients
    decision_variables = {}
    coefficients = {}
    #dummy var to hold objective
    objective = 0

    #for every line in the model formulation
    for x in model_lines:
        x_list = x.rsplit(' ')

        #if x is a variable declaration
        if x_list[0] == 'var':
            #if x is an indexed var declaration
            if "[" in x_list[1]:
                num_indexes = x_list[1].count('[')
                #if single index var
                if num_indexes == 1:
                    new_index_var_1 = []

                    #create vars for various indexes
                    for i in range(0,int(x_list[1].rsplit('[')[1].rsplit(']')[0])):
                        #create based on type
                        if x_list[-1] == 'int':
                            new_index_var_1.append(solver.IntVar(0,infinity, x_list[1].rsplit("[")[0] + str(i)))
                        elif x_list[-1] == 'num':
                            new_index_var_1.append(solver.NumVar(0,infinity, x_list[1].rsplit("[")[0] + str(i)))
                        elif x_list[-1] == 'binary':
                            new_index_var_1.append(solver.IntVar(0,1, x_list[1].rsplit("[")[0] + str(i)))
                elif num_indexes == 2:
                    print("TODO support multidimensional arrays")

                #append to decision variables list
                decision_variables[x_list[1].rsplit("[")[0]] = new_index_var_1
            else:
                    if x_list[-1] == 'int':
                        decision_variables[x_list[1]] = solver.IntVar(0,infinity, x_list[1])
                    elif x_list[-1] == 'num':
                        decision_variables[x_list[1]] = solver.NumVar(0,infinity, x_list[1])
                    elif x_list[-1] == 'binary':
                        decision_variables[x_list[1]] = solver.IntVar(0,1, x_list[1])
                    print(decision_variables)
        elif x_list[0] == 'coef':
            if "[" in x_list[1]:
                num_index = x_list[1].count("[")
                if num_index == 1:
                    #read in parameter file TODO: convert to uploader
                    coef_input = pd.read_csv(filepath_or_buffer=f"../parameters/{x_list[1].rsplit('[')[0]}", header=None)
                    coefficients[x_list[1].rsplit("[")[0]] = pd.Series.tolist(coef_input[0])
                    print(coefficients["a"])
                elif num_index ==2:
                    #todo suppot multi dimensional arrayus
                    print("TODO")

        elif (x_list[0] == 'max') | (x_list[0] == 'min'):
            obj_str = ' '.join(x_list[1:])
            print(obj_str)
            obj_expr = 0

            pieces = obj_str.rsplit(" ")
            if pieces == "":
                pieces = obj_str
            lead_sign = '+'
            for x in pieces:
                if x[0] in coefficients:
                    current_co = coefficients[x[0]]
                    current_v = decision_variables[x[-1]]

                    for i in range(0,len(current_co)):
                        if lead_sign == '+':
                            obj_expr += float(current_co[i]) * current_v[i]
                        else:
                            obj_expr += -(float(current_co[i]) * current_v[i])
                elif x == '+':
                    lead_sign = '+'

                elif x == '-':
                    lead_sign = '-'
                else:
                    if lead_sign == '+':
                        obj_expr += float(x[0])*decision_variables[x[-1]]
                    else:
                        obj_expr += float(x[0])*decision_variables[x[-1]]
            if(x_list[0] == 'max'):
                objective = solver.Maximize(obj_expr)
            elif(x_list[0] == 'min'):
                objective = solver.Minimize(obj_expr)
                print(obj_expr)

            print(objective)

        # if it is a constraint
        else:
            const_expr = 0
            const_ineq = 0
            const_end = 0

            const_str = ' '.join(x_list[0:])
            pieces = const_str.rsplit(" ")
            if pieces == "":
                pieces =const_str
            lead_sign = '+'
            for x in pieces:
                print("top")
                print(x)
                if x[0] in coefficients:
                    current_co = coefficients[x[0]]
                    current_v = decision_variables[x[-1]]
                    for i in range(0,len(current_co)):
                        if lead_sign == '+':
                            const_expr += float(current_co[i]) + current_v[i]
                        else:
                            const_expr += -(float(current_co[i]) + current_v[i])
                elif x[-1] in decision_variables:
                    print('new')
                    print(x[-1])
                    if type(decision_variables[x[-1]]) is list:
                        for dv in decision_variables[x[-1]]:
                            if lead_sign == '+':
                                const_expr += float(x[0:-2])*dv
                            else:
                                const_expr += -float(x[0:-2])*dv
                    elif lead_sign == '+':
                        const_expr += float(x[0:-2])*decision_variables[x[-1]]
                    else:
                        const_expr += -(float(x[0:-2]) *decision_variables[x[-1]])
                elif x == '+':
                    lead_sign = '+'
                elif x == '-':
                    lead_sign = '-'
                elif x == '>=':
                    const_ineq = '>='
                elif x == '==':
                    const_ineq = '=='
                elif x == "<=":
                    const_ineq = "<="
                else:
                    if lead_sign == '+':
                            const_end = float(x)
                    else:
                            const_end = -float(x)

            print(const_ineq)
            if const_ineq == "<=":
                print(const_end)
                print(const_expr)
                solver.Add(const_expr  <=  const_end)
            elif const_ineq == ">=":
                solver.Add(const_expr  >=  const_end)
            elif const_ineq == "==":
                solver.Add(const_expr  ==  const_end)

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print('opt-value')
        print(solver.Objective().Value())
        for x in solver.variables():
            print(x.SolutionValue())

def main():
    parse_text_to_model("""var y int\nvar x[8] int\ncoef a[]\nmax 199999*y + a*x\n100*y <= 10\n1*x <= 5""")

if __name__ == "__main__":
    main()