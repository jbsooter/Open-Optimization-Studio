import folium
import pandas as pd
import pydeck as pdk
import streamlit_folium
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from utilities import config

import streamlit as st
from routingpy import MapboxOSRM, ORS
from geopy.geocoders import MapBox


def query_matrix(nodes):
    '''
    Takes a list of coordinate pairs (lon,lat) and returns matrix based on configured/selected
    provider, distance/duration return type, and traveller profile
    :param nodes:
    :return: matrix of appropriate arc costs
    '''
    matrix = None
    if config.vrp_opts["matrix_provider"] == 'Mapbox':
        client = MapboxOSRM(api_key=st.secrets["matrix_key"])
        matrix = client.matrix(locations=nodes,profile=st.session_state["matrix_profile"],annotations=[st.session_state["matrix_metric"]])
    elif config.vrp_opts["matrix_provider"] == 'ORS':
        client = ORS(api_key=st.secrets["matrix_key"])
        matrix = client.matrix(locations=nodes,profile=st.session_state["matrix_profile"],metrics=[st.session_state["matrix_metric"]])

    if st.session_state["matrix_metric"] == 'distance':
        #st.write(matrix.distances)
        return matrix.distances
    else:
        #st.write(matrix.durations)
        return matrix.durations

def geocode_addresses(addresses):
    '''
    Take a list of addresses and convert to coordinate pairs.
    :param addresses:
    :return: list of coordinate pairs (lon,lat)
    '''
    geolocator = MapBox(api_key=st.secrets["geocoding_key"])

    coordinates = []
    for location in addresses:
        result = geolocator.geocode(location)
        coordinates.append([result.longitude, result.latitude])

    return coordinates

def generic_vrp(addresses):
    nodes = geocode_addresses(addresses)
    #identify depot
    depot_index = 0

    st.write(st.session_state["input_addresses"])

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
        return query_matrix(nodes=nodes)[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(addresses,nodes, manager, routing, solution)
    else:
        print('No solution found !')




#TODO: MODIFY TO BUILD MAP
#will need to get polylines from route of routingpy
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

        #TODO: support ORS here
        client = MapboxOSRM(api_key=st.secrets["matrix_key"])
        route = client.directions(locations=node_coordinates,profile=st.session_state["matrix_profile"])
        #st.write(route.geometry)
        map_df = pd.DataFrame(route.geometry)
        map_df.rename(columns = {0: "LON",1:"LAT"},inplace=True)
        #st.map(map_df)

        # use the response
        mls = map_df


        coords = []
        for x in route.geometry:
            coords.append([x[1],x[0]])

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

def displays():
    st.write(st.session_state.addresses_df)
def main():
    #add session state location for addresses
    if 'input_addresses' not in st.session_state:
        st.session_state["input_addresses"] = pd.DataFrame()

    #configure traveller profile and cost type
    st.selectbox(label="Traveller Profile",options=config.vrp_opts["matrix_profile_opts"],key='matrix_profile')
    st.selectbox(label = "Arc Cost Type",options=["distance","duration"],key="matrix_metric")

    #select number of vehicles
    st.text_input("Number of Vehicles",key="num_vehicles",value=1)


    #input addresses
    st.session_state.addresses_df = pd.DataFrame(
        {"Address to Visit":["800 W Dickson St, Fayetteville, Ar 72701","1270 W Leroy Pond Dr, Fayetteville, AR 72701"],"depot":[True,False]}
    )
    st.session_state["input_addresses"] = st.experimental_data_editor(data=st.session_state["addresses_df"],num_rows="dynamic",key="edited_addresses_df",on_change=displays)

    #run address query
    st.button("Run Matrix Query",on_click=generic_vrp,args=[(st.session_state["input_addresses"])["Address to Visit"]])

if __name__ == "__main__":
    main()