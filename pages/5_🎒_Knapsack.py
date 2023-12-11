import time

import pandas as pd
import streamlit as st
import altair as alt

from ortools.algorithms.python import knapsack_solver

def solve_instance(knapsack_data, algorithm):
    st.session_state["Knapsack_Solution"] = []
    for alg in algorithm:
        solver = knapsack_solver.KnapsackSolver(
            alg,
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

        st.session_state["Knapsack_Solution"].append([computed_value,total_weight, packed_items, packed_weights, solution_time_ns, alg])

def main():
    st.set_page_config(
        page_icon="🎒"
    )
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
    with st.sidebar:
        st.number_input(label="Knapsack Size",min_value= 1, max_value=1000,value=15, step=5, key="Knapsack_Size")

        opts = [
            knapsack_solver.SolverType.KNAPSACK_BRUTE_FORCE_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_64ITEMS_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_DYNAMIC_PROGRAMMING_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_DIVIDE_AND_CONQUER_SOLVER,
            knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_CBC_MIP_SOLVER,
            ]

        #de facto toString() for solver type objects
        def format_alg(alg):
            return str(alg).rsplit(".")[1].rsplit("K_")[1]
        algo_selection = st.multiselect(label='Algorithm',options=opts, format_func = format_alg)
        st.button(label="Solve",on_click=solve_instance, args=[item_data, algo_selection])

    if st.session_state["Knapsack_Solution"] is not None:
        data_time = {"Algorithm":[],"Solution Time": [], "Solution": []}

        for x in st.session_state["Knapsack_Solution"]:
            data_time["Algorithm"].append(format_alg(x[5]))
            data_time["Solution Time"].append(x[4]/1000000000.0)
            data_time["Solution"].append(x[0])

        #time and solution bar chart data
        df = pd.DataFrame(data_time)

        chart_time = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("Algorithm:O", sort="y", axis=alt.Axis(labelAngle=-45, labelLimit=500 )),
                y=alt.Y(
                        "Solution Time:Q",
                        title="Solution Time (ns)"
                        ),
            )
            .properties(width=700, height=500)
        )

        chart_sol = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("Algorithm:O", sort="y", axis=alt.Axis(labelAngle=-45, labelLimit=500 )),
                y=alt.Y(
                    "Solution:Q",
                    title="Solution"
                ),
            )
            .properties(width=700, height=500)
        )

        st.altair_chart((chart_time))
        st.altair_chart(chart_sol)

        columns = ["Algorithm", "Optimal Solution", "Solve Time (ns)", "Total Weight", "Packed Items"]
        table_data = []

        # Loop through each solution in the Knapsack_Solution state
        for x in st.session_state["Knapsack_Solution"]:
            row = [format_alg(str(x[5])), x[0], x[4], x[1], x[2]]
            table_data.append(row)

        df = pd.DataFrame(table_data, columns=columns)

        # Display the DataFrame as a table
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()