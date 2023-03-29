import folium
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

#ORS client to be shared among all methods
client = None
if config.vrp_opts["ors_server"] == "Default":
    client = openrouteservice.Client(key=st.secrets["ors_key"])
else:
    client = openrouteservice.Client(key=st.secrets["ors_key"],base_url=config.vrp_opts["ors_server"])
def query_matrix(nodes):
    '''
    Takes a list of coordinate pairs (lon,lat) and returns matrix based on configured/selected
    provider, distance/duration return type, and traveller profile
    :param nodes:
    :return: matrix of appropriate arc costs
    '''

    matrix = distance_matrix.distance_matrix(client,locations=nodes,profile=st.session_state["matrix_profile"])
    return matrix["durations"]
def geocode_addresses(addresses):
    '''
    Take a list of addresses and convert to coordinate pairs.
    :param addresses:
    :return: list of coordinate pairs (lon,lat)
    '''

    coordinates = []
    for location in addresses:
        result = pelias_search(client=client,text=location)
        coordinates.append([result["bbox"][0], result["bbox"][1]])

    return coordinates

def generic_vrp(addresses):
    nodes = geocode_addresses(addresses)
    #identify depot
    depot_index = 0

    #query cost matrix
    arc_cost_matrix = query_matrix(nodes=nodes)
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(arc_cost_matrix),
                                           int(st.session_state['num_vehicles']), depot_index)

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

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.solution_limit = 1

    #create solutionCollector
    all_solutions = routing.solver().AllSolutionCollector()

    #give access to node vars
    for node in range(len(arc_cost_matrix)):
        all_solutions.Add(routing.NextVar(manager.NodeToIndex(node)))

    for v in range(int(st.session_state["num_vehicles"])):
        all_solutions.Add(routing.NextVar(routing.Start(v)))

    #add as monitor to solver
    routing.AddSearchMonitor(all_solutions)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    #give access to objective var
    all_solutions.AddObjective(routing.CostVar())

    st.write(all_solutions.SolutionCount())

    #add as monitor to solver
    routing.AddSearchMonitor(all_solutions)
    # Solve the problem fully.
    search_parameters.solution_limit = 10

    solution = routing.SolveWithParameters(search_parameters)
    # Print solution on console.
    if solution:
        #for i in range(1,all_solutions.SolutionCount()): #1 to skip repeat initial
        st.write(all_solutions.ObjectiveValue(all_solutions.SolutionCount()-1))
        print_solution(addresses,nodes, manager, routing, all_solutions.Solution(all_solutions.SolutionCount()-1))

        #chart improvement
        x = []
        y = []
        for i in range(1,all_solutions.SolutionCount()): #1 to skip repeat initial
            x.append(i)
            y.append(all_solutions.ObjectiveValue(i))

        # plot
        fig, ax = plt.subplots()

        ax.plot(x, y)

        st.pyplot(fig=fig)

    else:
        print('No solution found !')

def print_solution(addresses,nodes, manager, routing, solution):
    """Prints solution on console."""
    st.write(f'Objective: {solution.ObjectiveValue()}')
    max_route_distance = 0
    m = folium.Map()
    for vehicle_id in range(int(st.session_state["num_vehicles"])):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        node_coordinates = []
        while not routing.IsEnd(index):
            #build input for route
            node_coordinates.append(nodes[manager.IndexToNode(index)])
            #plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))

            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        #plan_output += '{}\n'.format(manager.IndexToNode(index))
        node_coordinates.append(nodes[manager.IndexToNode(index)])
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        st.write(plan_output)
        max_route_distance = max(route_distance, max_route_distance)

        route = directions(client=client,coordinates=node_coordinates,profile=st.session_state["matrix_profile"])

        coords = decode_polyline(route["routes"][0]["geometry"],False)
        #add the nodes
        for i in range(0,len(node_coordinates)-1): #TODO: double check this range
            folium.Marker([node_coordinates[i][1],node_coordinates[i][0]],popup=addresses[i]).add_to(m)
        # add the lines
        folium.PolyLine(coords, weight=5, opacity=1,color=config.vrp_opts["folium_colors"][vehicle_id]).add_to(m)
    # create optimal zoom
    nodes_all_df = pd.DataFrame(nodes).rename(columns={0:'Lon', 1:'Lat'})[['Lat', 'Lon']]
    sw = nodes_all_df[['Lat', 'Lon']].min().values.tolist()
    ne = nodes_all_df[['Lat', 'Lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

    streamlit_folium.folium_static(m,width=700)

def rate_limited_generic_vrp(addresses):
    '''
    Imposes the configured limit on the size of problem instance to avoid exhausting the API key inadvertently.
    :param addresses:
    :return:
    '''
    if len(addresses.index) >  config.vrp_opts["max_num_nodes"]:
        st.write(f"Your problem instance is larger than the maximum configured size of {config.vrp_opts['max_num_nodes']}")
    else:
        generic_vrp(addresses)
def main():
    #add session state location for addresses
    if 'input_addresses' not in st.session_state:
        st.session_state["input_addresses"] = pd.DataFrame()

    #configure traveller profile and cost type
    st.selectbox(label="Traveller Profile",options=config.vrp_opts["ors_matrix_profile_opts"],key='matrix_profile')

    #select number of vehicles
    st.text_input("Number of Vehicles",key="num_vehicles",value=1)

    #input addresses
    st.session_state.addresses_df = pd.DataFrame(
        {"Address to Visit":["800 W Dickson St, Fayetteville, Ar 72701","1270 W Leroy Pond Dr, Fayetteville, AR 72701"],"depot":[True,False]}
    )
    st.session_state["input_addresses"] = st.experimental_data_editor(data=st.session_state["addresses_df"],num_rows="dynamic",key="edited_addresses_df")

    #run address query
    st.button("Run Optimization",on_click=rate_limited_generic_vrp,args=[(st.session_state["input_addresses"])["Address to Visit"]])

if __name__ == "__main__":
    main()