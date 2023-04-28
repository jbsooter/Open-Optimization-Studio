import folium
import numpy as np
import pandas as pd
import streamlit_folium
import openrouteservice
import streamlit as st
from matplotlib import pyplot as plt

from openrouteservice import distance_matrix
from openrouteservice.directions import directions
from openrouteservice.geocode import pelias_search
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from utilities.utility_functions import decode_polyline
from utilities import config

# ORS client to be shared among all methods
client = None
if config.vrp_opts["ors_server"] == "Default":
    client = openrouteservice.Client(key=st.secrets["ors_key"])
else:
    client = openrouteservice.Client(
        key=st.secrets["ors_key"],
        base_url=config.vrp_opts["ors_server"])


def query_matrix(nodes):
    '''
    Takes a list of coordinate pairs (lon,lat) and returns matrix based on configured/selected
    provider, distance/duration return type, and traveller profile
    :param nodes:
    :return: matrix of appropriate arc costs
    '''

    matrix = distance_matrix.distance_matrix(
        client, locations=nodes, profile=st.session_state["matrix_profile"], metrics=['distance','duration'], units='mi')
    if st.session_state["cost_metric"] == 'distance':
        return matrix["distances"]
    elif st.session_state['cost_metric'] == 'duration':
        return matrix["durations"]


def geocode_addresses(addresses):
    '''
    Take a list of addresses and convert to coordinate pairs.
    :param addresses:
    :return: list of coordinate pairs (lon,lat)
    '''

    coordinates = []
    for location in addresses:
        result = pelias_search(client=client, text=location)
        coordinates.append([result["bbox"][0], result["bbox"][1]])

    return coordinates


def generic_vrp(addresses):
    if 'vrp_solution' not in st.session_state:
        st.session_state['vrp_solution'] = {
            'text': None, 'map': None, 'improvement': None}
    nodes = geocode_addresses(addresses)
    # identify depot
    depot_index = 0

    # query cost matrix
    arc_cost_matrix = query_matrix(nodes=nodes)
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(arc_cost_matrix), int(
            st.session_state['num_vehicles']), depot_index)

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return arc_cost_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # add homogenous vehicle capacity
    def cb(a,b):
        if(a != 0 ) & (b != 0):
            return 1
        else:
            #no cost to capacity if depot
            return 0
    demand_callback_index = routing.RegisterTransitCallback(cb)
    routing.AddDimension(demand_callback_index,0,st.session_state["vehicle_capacity"],True,'capacity')

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.solution_limit = 1

    # create solutionCollector
    all_solutions = routing.solver().AllSolutionCollector()

    # give access to node vars
    for node in range(len(arc_cost_matrix)):
        all_solutions.Add(routing.NextVar(manager.NodeToIndex(node)))

    for v in range(int(st.session_state["num_vehicles"])):
        all_solutions.Add(routing.NextVar(routing.Start(v)))

    # add as monitor to solver
    routing.AddSearchMonitor(all_solutions)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # give access to objective var
    all_solutions.AddObjective(routing.CostVar())

    # add as monitor to solver
    routing.AddSearchMonitor(all_solutions)
    # Solve the problem fully.
    search_parameters.solution_limit = 10

    solution = routing.SolveWithParameters(search_parameters)
    # Print solution on console.
    if solution:
        # for i in range(1,all_solutions.SolutionCount()): #1 to skip repeat
        # initial
        st.write(all_solutions.ObjectiveValue(
            all_solutions.SolutionCount() - 1))
        print_solution(
            addresses,
            nodes,
            manager,
            routing,
            all_solutions.Solution(
                all_solutions.SolutionCount() -
                1))

        # chart improvement
        x = []
        y = []
        for i in range(
                1, all_solutions.SolutionCount()):  # 1 to skip repeat initial
            x.append(i)
            y.append(all_solutions.ObjectiveValue(i))

        if len(y) > 1:
            # plot
            fig, ax = plt.subplots()
            ax.set_title("Objective vs Metahueristic Iteration")

            ax.plot(x, y)
            ax.set_xlabel('Metaheuristic Iteration')
            ax.set_ylabel('Objective Value')

            #set x ticks to be integer over all iterations
            plt.xticks(np.arange(1,all_solutions.SolutionCount(),1))

            st.session_state['vrp_solution']['improvement'] = fig
        else:
            st.session_state['vrp_solution']['improvement'] = None

    else:
        st.session_state['vrp_solution']['text'] = ["No solution found !"]
        st.session_state['vrp_solution']['improvement'] = None
        st.session_state['vrp_solution']['map'] = None


def print_solution(addresses, nodes, manager, routing, solution):
    """Prints solution on console."""
    text_solution = []
    text_solution.append(f'Objective: {solution.ObjectiveValue()}\n')
    max_route_distance = 0
    m = folium.Map()
    routes_all = []
    for vehicle_id in range(int(st.session_state["num_vehicles"])):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}: '.format(vehicle_id)
        route_distance = 0
        node_coordinates = []
        while not routing.IsEnd(index):
            # build input for route
            if index < len(addresses):
                node_coordinates.append(
                    {'index': index, 'coordinates': nodes[manager.IndexToNode(index)]})
            else:  # set index in dict of artificial depot to 0
                node_coordinates.append(
                    {'index': 0, 'coordinates': nodes[manager.IndexToNode(index)]})
            plan_output += ' {} -> '.format(
                addresses[manager.IndexToNode(index)])
            previous_index = index
            index = solution.Value(routing.NextVar(index))

            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)

        plan_output += '{}\n'.format(addresses[manager.IndexToNode(index)])
        text_solution.append(plan_output)
        if index < len(addresses):
            node_coordinates.append(
                {'index': index, 'coordinates': nodes[manager.IndexToNode(index)]})
        else:  # set index in dict of artificial depot to 0
            node_coordinates.append(
                {'index': 0, 'coordinates': nodes[manager.IndexToNode(index)]})
        text_solution.append(
            'Cost of the route: {} \n'.format(route_distance))
        max_route_distance = max(route_distance, max_route_distance)

        route = directions(
            client=client,
            coordinates=[
                x["coordinates"] for x in node_coordinates],
            profile=st.session_state["matrix_profile"])

        coords = decode_polyline(route["routes"][0]["geometry"], False)
        # add the nodes
        for i in range(0, len(
                node_coordinates)):  # -1 because depot included twice once at begin once at end
            folium.Marker([node_coordinates[i]["coordinates"][1],
                           node_coordinates[i]["coordinates"][0]],
                          popup=addresses[node_coordinates[i]["index"]]).add_to(m)
        # add the lines
        folium.PolyLine(
            coords,
            weight=5,
            opacity=1,
            color=config.vrp_opts["folium_colors"][vehicle_id]).add_to(m)
        routes_all.append(route)
    # create optimal zoom
    nodes_all_df = pd.DataFrame(nodes).rename(
        columns={0: 'Lon', 1: 'Lat'})[['Lat', 'Lon']]
    sw = nodes_all_df[['Lat', 'Lon']].min().values.tolist()
    ne = nodes_all_df[['Lat', 'Lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

    st.session_state['vrp_solution']['map'] = m
    st.session_state['vrp_solution']['text'] = text_solution
    st.session_state['vrp_solution']['routes'] = routes_all


def rate_limited_generic_vrp(addresses):
    '''
    Imposes the configured limit on the size of problem instance to avoid exhausting the API key inadvertently.
    :param addresses:
    :return:
    '''
    if len(addresses.index) > config.vrp_opts["max_num_nodes"]:
        st.write(
            f"Your problem instance is larger than the maximum configured size of {config.vrp_opts['max_num_nodes']}")
    else:
        generic_vrp(addresses)


def main():
    st.subheader("Vehicle Routing")
    with st.sidebar:
        st.write("[Docs](https://jbsooter.github.io/Open-Optimization-Studio/Vehicle%20Routing)")
    # add session state location for addresses
    if 'input_addresses' not in st.session_state:
        st.session_state["input_addresses"] = pd.DataFrame()

    # configure traveller profile and cost type
    st.selectbox(
        label="Traveller Profile",
        options=config.vrp_opts["ors_matrix_profile_opts"],
        key='matrix_profile')

    st.selectbox(
        label="Cost Metric",
        options=config.vrp_opts["cost_metrics"],
        key='cost_metric',
        help='distance is in miles, duration is in seconds'
    )

    # select number of vehicles
    st.number_input("Number of Vehicles", key="num_vehicles", value=1,step=1)

    # select vehicle capacity
    st.number_input("Vehicle Order Capacity", key="vehicle_capacity",value=3,step=1)

    # input addresses
    st.session_state.addresses_df = pd.DataFrame(
        {
            "Address to Visit": [
                "800 W Dickson St, Fayetteville, Ar 72701",
                "1270 Nolan Richardson Dr, Fayetteville, AR 72701",
                "3919 N Mall Ave, Fayetteville, AR 72703"],
            "depot": [
                True,
                False,
                False]})
    st.session_state["input_addresses"] = st.experimental_data_editor(
        data=st.session_state["addresses_df"],
        num_rows="dynamic",
        key="edited_addresses_df")

    # run address query
    st.button("Run Optimization", on_click=rate_limited_generic_vrp, args=[
              (st.session_state["input_addresses"])["Address to Visit"]])

    if 'vrp_solution' in st.session_state:
        for x in st.session_state['vrp_solution']['text']:
            st.write(x)

        if st.session_state['vrp_solution']['map'] is not None:
            streamlit_folium.folium_static(
                st.session_state['vrp_solution']['map'], width=700)
        if st.session_state['vrp_solution']['improvement'] is not None:
            st.pyplot(st.session_state['vrp_solution']['improvement'])
        if st.session_state['vrp_solution']['routes'] is not None:
            with st.expander(label="Detailed Directions"):
                veh_count = 1
                for x in st.session_state['vrp_solution']['routes']:
                    st.subheader(f"Vehicle {veh_count}")
                    for y in x["routes"][0]["segments"]:
                        for z in y["steps"]:
                            st.write(z["instruction"])
                    veh_count = veh_count + 1



if __name__ == "__main__":
    main()
