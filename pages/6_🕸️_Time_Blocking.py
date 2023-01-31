import pandas as pd
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

def main():
    st.write("coming soon!")

if __name__ == "__main__":
    main()