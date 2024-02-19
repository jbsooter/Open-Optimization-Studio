import math

import folium
import gspread
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from streamlit_folium import st_folium
from geopy.distance import geodesic

import utilities.config

st.set_page_config(layout='wide')

def validate_tsp_solution(polylines, cities):
    """Validate if the given set of polylines is a solution to the TSP for the given cities."""
    path = []
    missing = []

    for name, city in cities.items():
        incCount = 0

        for ltlng in polylines[0]["coordinates"][:-1]:

            if math.isclose(ltlng[0], city[1], abs_tol=0.05)&math.isclose(ltlng[1], city[0], abs_tol=0.05):
                incCount += 1
        if incCount == 1:
            path.append(city)
        elif incCount == 0:
            missing.append(name)

    if len(path) == len(cities):
        return [True, "Valid Solution"]
    else:
        return [False, "Infeasible Solution. Must Visit All Cities Once and Only Once. Missing cities:   " + str(missing)]

def main():
    st.subheader("Travelling Salesman Game")
    st.markdown("Given a list of cities and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the origin city?")

    with st.expander("Instructions"):
        st.markdown("**To build a solution**: First, enter your team name on the sidebar. This is required to submit a solution. Use the polyline button to connect the cities shown on the map below. Cities must be connected using a single polyline object. "
                    "An existing polyline can be disposed of using the trash button, or its nodes rearranged using the edit button. After a polyline has been constructed,"
                    " below the graph you will recieve the total distance, whether or not your solution is feasible, and the ability to submit it to the leaderboard. ")
        colL, colR, colB = st.columns([0.25,1,8])
        colL.image('images/tsp_polyline.png')
        colR.write("polyline button")
        colL.image('images/tsp_edit.png')
        colR.write("edit button")
        colL.image('images/tsp_trash.png')
        colR.write("trash button")



    with st.sidebar:
        name = st.text_input("Team Name", key="team_name_tsp")
        st.radio(label="Instance",key ="tsp_instance", options=["Arkansas","South_Central","Airports"], on_change=read_scores)
        if "leaderboard" not in st.session_state:
            st.session_state["leaderboard"] = None
            read_scores()
        st.subheader("Leaderboard")
        st.dataframe(st.session_state["leaderboard"])



    #find centroid
    total_lat = 0
    total_lon = 0
    num_locations = len(utilities.config.tsp_game_opts[st.session_state["tsp_instance"]])

    for city, (lat, lon) in utilities.config.tsp_game_opts[st.session_state["tsp_instance"]].items():
        total_lat += lat
        total_lon += lon

    average_lat = total_lat / num_locations
    average_lon = total_lon / num_locations


    m = folium.Map(location=[average_lat,average_lon], zoom_start=6) #centroid
    for city, coord in utilities.config.tsp_game_opts[st.session_state["tsp_instance"]].items():
        folium.Circle(location=coord, popup=city, radius=5000).add_to(m)
        #folium.Marker(location=coord,popup=city).add_to(m)
    Draw(export=True).add_to(m)

    output = st_folium(m,  height = 800,use_container_width=True)

    heur_result = solve_heuristic(st.session_state["tsp_instance"])
    total_distance = 0

    if output["all_drawings"] is not None:
        if len(output["all_drawings"]) != 0:
            polylines_only = []

            for i in range(0, len(output["all_drawings"][0]["geometry"]["coordinates"])-1):

                    a = output["all_drawings"][0]["geometry"]["coordinates"][i]
                    b = output["all_drawings"][0]["geometry"]["coordinates"][i+1]

                    total_distance += geodesic((a[1],a[0]),(b[1],b[0])).miles

            polylines_only.append(output["all_drawings"][0]["geometry"])

            col1,col2,col3,col4,col5 = st.columns([1,1,1,1,1])
            col1.write("Total Distance (mi):   " + str(round(total_distance,3)))
            col3.write("Gap from Computer Solution: " + str(round(100*(total_distance - heur_result[2])/heur_result[2],2)) + "%")
            val = validate_tsp_solution(polylines_only, utilities.config.tsp_game_opts[st.session_state["tsp_instance"]])
            col2.write(val[1])
            col4.button("Submit Score",on_click=write_scores, args=[name, total_distance,val])



def write_scores(name, total_distance, val):
    '''Write a valid score to Google Sheets List, otherwise display error message. Regardless, retrieve a new read of scoreboard. '''
    st.write(st.session_state["team_name_tsp"] )
    if ((st.session_state["team_name_tsp"] != "")):
        if val[0]:
            gc = gspread.service_account_from_dict(st.secrets["google_sheets"])

            scoreboard = gc.open("TSP").worksheet("Scores")

            scoreboard.append_row([name, total_distance, st.session_state["tsp_instance"]])
            scoreboard.sort((2,'asc'))
        else:
            st.error(val[1])

    else:
        st.error("Submission Error. No Team Name")
    read_scores()

def read_scores():
    gc = gspread.service_account_from_dict(st.secrets["google_sheets"])
    scoreboard = gc.open("TSP").worksheet("Scores")

    leaders = pd.DataFrame(scoreboard.get_all_records())
    leaders = leaders.drop(leaders[(leaders == 0).any(axis=1)].index)
    leaders = leaders[leaders["Instance"] == st.session_state["tsp_instance"]]
    st.session_state["leaderboard"]= leaders

@st.cache_data
def solve_heuristic(tsp_instance):
    def create_data_model(locations):
        data = {}
        data['locations'] = locations
        data['num_locations'] = len(locations)
        data['num_vehicles'] = 1
        data['depot'] = 0
        return data

    def distance_matrix_haversine(locations):
        matrix = []
        for from_node in locations:
            row = []
            for to_node in locations:
                if from_node == to_node:
                    row.append(0)
                else:
                    lat1, lon1 = locations[from_node]
                    lat2, lon2 = locations[to_node]
                    distance = geodesic((lat1,lon1),(lat2,lon2)).miles
                    row.append(distance)
            matrix.append(row)
        return matrix

    data = create_data_model(utilities.config.tsp_game_opts[st.session_state["tsp_instance"]])
    distance_matrix = distance_matrix_haversine(data['locations'])

    manager = pywrapcp.RoutingIndexManager(data['num_locations'], data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.SAVINGS)
    search_parameters.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC)

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        index = routing.Start(0)
        plan_output = []
        total_distance = 0
        while not routing.IsEnd(index):
            from_node = manager.IndexToNode(index)
            plan_output.append(list(utilities.config.tsp_game_opts[st.session_state["tsp_instance"]])[manager.IndexToNode(index)])

            index = solution.Value(routing.NextVar(index))
            to_node = manager.IndexToNode(index)
            total_distance = total_distance +  distance_matrix[from_node][to_node]
        to_node = manager.IndexToNode(index)
        plan_output.append(list(utilities.config.tsp_game_opts[st.session_state["tsp_instance"]])[manager.IndexToNode(index)])
        total_distance += distance_matrix[from_node][to_node]
        return [routing.status(), plan_output, total_distance]
    else:
        return 'No solution found.'
if __name__ == "__main__":
    main()