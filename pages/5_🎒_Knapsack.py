import time

import pandas as pd
import streamlit as st

from ortools.algorithms.python import knapsack_solver

def solve_instance(knapsack_data, algorithm):
    solver = knapsack_solver.KnapsackSolver(
        algorithm,
        "KnapsackExample",
    )
    solver.init(knapsack_data["Value"].astype(int).tolist(), [knapsack_data["Size"].astype(int).tolist()], [st.session_state["Knapsack_Size"]])

    start_time = time.perf_counter_ns()
    computed_value = solver.solve()
    solution_time_ns = time.perf_counter_ns() - start_time

    packed_items = []
    packed_weights = []
    total_weight = 0

    for i in range(len(knapsack_data["Name"].tolist())):
        if solver.best_solution_contains(i):
            packed_items.append(knapsack_data["Name"].tolist()[i])
            packed_weights.append(knapsack_data["Size"][i])
            total_weight += knapsack_data["Size"][i]

    st.session_state["Knapsack_Solution"] = [computed_value,total_weight, packed_items, packed_weights, solution_time_ns]

def main():
    st.subheader("Knapsack")

    if "Knapsack_Solution" not in st.session_state:
        st.session_state["Knapsack_Solution"] = None

    data = {
        'Name': ['Backpack', 'Clothes (3 outfits)', 'Toiletries (small bag)', 'Travel adapter', 'Water bottle', 'Snacks and other consumables', 'Guidebook', 'Camera', 'Headphones', 'First-aid kit', 'Phone charger & portable battery', 'Miscellaneous (pens, sunglasses, etc.)'],
        'Size': [9, 6, 3, 2, 4, 5, 4, 6, 4, 3, 3, 2],
        'Value': [8, 7, 5, 4, 2, 6, 3, 8, 6, 4, 5, 3]
    }


    knapsack_data = pd.DataFrame(data)
    item_data = st.data_editor(knapsack_data, num_rows='dynamic')

    st.number_input(label="Knapsack Size",min_value= 1, max_value=1000,value=15, step=5, key="Knapsack_Size")

    opts = [
            knapsack_solver.SolverType.KNAPSACK_BRUTE_FORCE_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_64ITEMS_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_DYNAMIC_PROGRAMMING_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_DIVIDE_AND_CONQUER_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_CBC_MIP_SOLVER,
            ]

    algo_selection = st.selectbox(label='Algorithm',options=opts)
    st.button(label="Solve",on_click=solve_instance, args=[item_data, algo_selection])

    if st.session_state["Knapsack_Solution"] is not None:
        st.write("Optimal Solution: " + str(st.session_state["Knapsack_Solution"][0]))
        st.write("Solve Time (ns): " + str(st.session_state["Knapsack_Solution"][4]))
        st.write("Total Weight in Knapsack: " + str(st.session_state["Knapsack_Solution"][1]))
        st.write("Packed Items: ")
        st.write(st.session_state["Knapsack_Solution"][2])


if __name__ == "__main__":
    main()