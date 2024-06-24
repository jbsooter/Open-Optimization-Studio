import datetime
import math
import time
from random import random

import geopandas
import networkx as nx
import numpy as np
import openrouteservice
import osmnx as osmnx
import requests
import streamlit as st
import streamlit_folium
import folium
import streamlit_searchbox
from matplotlib import pyplot as plt

from openrouteservice import geocode
from shapely import LineString
from io import BytesIO

from streamlit_js_eval import get_geolocation

from utilities import config

from utilities import one_all_mosp

#useful tag config
osmnx.settings.useful_tags_way=['bridge', 'tunnel', 'oneway', 'lanes', 'ref', 'name',
                                 'highway', 'maxspeed', 'service', 'access', 'area',
                                 'landuse', 'width', 'est_width', 'junction', 'surface','length','foot']

osmnx.settings.useful_tags_node = ['name','lit','amenity']

osmnx.settings.bidirectional_network_types = ['all']

#retrieve client
# ORS client to be shared among all methods
client = None
if config.trip_planning_opts["ors_server"] == "Default":
    client = openrouteservice.Client(key=st.secrets["ors_key"])
elif config.trip_planning_opts["ors_server"] == "Default-Personal":
    client = openrouteservice.Client(key=st.session_state["personal-ors-key"])
else:
    client = openrouteservice.Client(
        key=st.secrets["ors_key"],
        base_url=config.trip_planning_opts["ors_server"])

@st.cache_data(ttl= 2,show_spinner=False)
def pelias_autocomplete(searchterm: str) -> list[any]:
    #https://github.com/pelias/documentation/blob/master/autocomplete.md
    return [name["properties"]["label"] for name in geocode.pelias_autocomplete(client=client, text=searchterm)["features"]]

def build_cache_support(address, map_mode):
    #run build graph, if same, no queries, otherwise, queries update graph session state
    build_graph(address, map_mode, st.session_state["mileage"])
    #build route based on opt criteria
    build_route_mosp(address, map_mode,st.session_state["mileage"])

def route_similarity(routeA,routeB):
    sim_pct = 0
    for node in routeA:
        if node in routeB:
            sim_pct += 1

    if routeA[-1] != routeB[-1]:
        return sim_pct/min(len(routeA),len(routeB))
    else:
        return sim_pct/min(len(routeA),len(routeB)) + .1 #penalize same dest

# def dominance_check(sol1, sol2):
#     c = sol1
#     cc = sol2
#
#     counter = 0
#
#     for i in range(0,len(c)):
#         if c[i] <= cc[i]:
#             #count the better objectives
#             if c[i] < cc[i]:
#                 counter += 1
#         #if there is ever a worse, return false
#         if c[i] > cc[i]:
#             return False
#
#     if counter >= 1:
#         return True
#     else:
#         return False
#
#
# def pareto_sort(solutions):
#     dominance_count = [0] * len(solutions)
#
#     # calculate dominance count
#     for i in range(0,len(solutions)):
#         for j in range(0,len(solutions)):
#             if i != j:
#                 if dominance_check(solutions[i][3], solutions[j][3]):
#                     dominance_count[j] += 1
#         solutions[i].append(dominance_count[j])
#
#     #sort based on relative dominance
#     sorted_solutions = sorted(solutions, key=lambda x: x[6])
#     sorted_solutions.reverse()
#
#     return sorted_solutions

@st.cache_data()
def build_graph(address,map_mode, mileage):
    with st.spinner(text="Requesting Map Data"):
        if map_mode == True:
            rgs = []
            rgs_b = []
            #combine all the filtered data thats requested
            for x in config.running_opts["osmnx_network_filters"]:
                rgs.append(osmnx.graph_from_point(address, dist=1.1*mileage*1609.34/2, dist_type='bbox',
                                                                                                             simplify=False, retain_all=False, truncate_by_edge=False,custom_filter=x))
                rgs_b.append(osmnx.graph_from_point(address, dist=(1.0*mileage)*1609.34/2, dist_type='bbox',
                                                                                    simplify=False, retain_all=False, truncate_by_edge=False,custom_filter=x))
            #compose graphs and save in sess st
            st.session_state["running_graph"] = nx.compose_all(rgs)
            st.session_state["running_boundary_graph"] = nx.compose_all(rgs_b)

            st.session_state["address_coords"] = address
            st.session_state["select_map"] = False
        else:
            # query osm
            rgs = []
            rgs_b = []
            for x in config.running_opts["osmnx_network_filters"]:
                r_i, st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=1.1*mileage*1609.34/2, dist_type='bbox',
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,custom_filter=x, )
                rgs.append(r_i)
                rgs_b.append(osmnx.graph_from_address(address, dist=(1.0*mileage)*1609.34/2, dist_type='bbox',
                                                                                simplify=False, retain_all=False, truncate_by_edge=False, return_coords=False,custom_filter=x))
            st.session_state["running_graph"] = nx.compose_all(rgs)
            st.session_state["running_boundary_graph"] = nx.compose_all(rgs_b)

    with st.spinner(text="Requesting Elevation Data"):
        attempts = 0
        while True:
            try:
                attempts = attempts + 1
                #snippet to add elevation to entire graph.
                osmnx.elevation.add_node_elevations_google(st.session_state["running_graph"],None,
                                                       url_template = "https://api.open-elevation.com/api/v1/lookup?locations={}")

                break
            except:
                if attempts < 3:
                    st.error("Elevation Query Failed. Will Re-attempt in 10 seconds")
                    time.sleep(10) #pause ten seconds and try again
                else:
                    st.error("open-elevation.com appears to be experiencing downtime. Please try again later. ")
                    return



def type_cost(way):
    type_cost = 100
    if "highway" in way:
        if way["highway"] in ["primary","motorway","primary_link"]:
            type_cost = 100
        elif way["highway"] in ["service","residential","unclassified", "tertiary"]:
            type_cost = 50
    #prefer cycleways

    if way["highway"]  in ["cycleway","pedestrian","track","footway","path"]:
        type_cost  = 25

    if "foot" in way:
        if way["foot"] in ["designated","yes"]:
            type_cost = 25

    return type_cost*way["length"]

def turn_cost(way):
    turn_cost = 0
    if st.session_state["turn_type"] == "Many Turns":
        turn_cost = min(10000,way["length"])
    elif st.session_state["turn_type"] == "Few Turns":
        turn_cost =  max(10000-way["length"],0)
    return turn_cost

def elevation_cost(node_a, node_b, way):
    if st.session_state["elevation_type"] == "Flat":
        return abs((st.session_state["running_graph"].nodes()[node_b]["elevation"]-st.session_state["running_graph"].nodes()[node_a]["elevation"])/way["length"])
    elif st.session_state["elevation_type"]   == "Steep":
        #use 1/grade to prevent negative
        return np.nan_to_num(1.0,abs((st.session_state["running_graph"].nodes()[node_b]["elevation"]-st.session_state["running_graph"].nodes()[node_a]["elevation"])/way["length"]),nan=0)
def build_route_mosp(address,map_mode, mileage):
    if st.session_state["running_graph"] is None:
        build_graph(address, map_mode,mileage+.01)
    with st.spinner("Computing Routes"):
        for u, v, data in st.session_state["running_graph"].edges(data=True):
            data["costs"] = [elevation_cost(u,v,data),
                             turn_cost(data),
                             type_cost(data)
                             ]
        # set source and sink
        source_return = osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])
        #get node ids that are on the last graph 1-mi of the considered area
        rg_local = nx.MultiDiGraph(st.session_state["running_graph"])
        #osmnx.simplify_graph(rg_local)

        rbg_local = nx.MultiDiGraph(st.session_state["running_boundary_graph"])
        #osmnx.simplify_graph(rbg_local)
        result = [i for i in rg_local if i not in rbg_local]
        #guaruntee node uniwqueness
        result = set(result)
        result = list(result)
        #-----------

        L = one_all_mosp.one_to_all(st.session_state["running_graph"],source_return,3)

        results = []
        for label in L.values():
            label = label[-1]
            if label.node in result:
                if len(results) > 0:
                    add = True
                    for x in results:
                        if route_similarity(x[-1],label.label_list) < config.running_opts["similarity_pct"]:
                            continue
                        else:
                            add = False
                            break
                    if add:
                        length_m = 0
                        for i in range(0,len(label.label_list)-1):
                            length_m += st.session_state["running_graph"][label.label_list[i]][label.label_list[i+1]][0]["length"]*2

                        results.append([st.session_state["running_graph"].subgraph(label.label_list),source_return,label.node,label.costs,length_m,label.label_list])
                else:
                    length_m = 0
                    for i in range(0,len(label.label_list)-1):
                        length_m += st.session_state["running_graph"][label.label_list[i]][label.label_list[i+1]][0]["length"]*2
                    results.append([st.session_state["running_graph"].subgraph(label.label_list),source_return,label.node,label.costs,length_m,label.label_list])

        #results = pareto_sort(results)
        results = sorted(results, key = lambda x:sum(x[3]))
        results = results[0:10]

        st.session_state["running_route_results"] = results
        st.session_state["route_iter"] = 0
        st.session_state["route_iter_max"] = len(results)

@st.cache_data(ttl=15*60) #refresh 15 min
def nws_api():
    #weather
    URL = f'https://api.weather.gov/points/{st.session_state["address_coords"][0]},{st.session_state["address_coords"][1]}'

    response = requests.get(URL)

    URL = response.json()['properties']['forecastHourly']
    attempts = 0
    while True:
        try:
            attempts = attempts + 1
            response = requests.get(URL)
            break
        except:
            if attempts < 3:
                st.error("National Weather Service Query Failed. Will Try again in 10 seconds. ")
                time.sleep(10) #pause ten seconds and try again
            else:
                st.error("The National Weather Service API appears to be experiencing downtime. Please try again later. ")

    # Limiting to the first 10 periods
    response_json = response.json()

    md_table = ""
    # Extract times and data
    times = [datetime.datetime.fromisoformat(x["startTime"]).strftime("%I:%M %p") for x in response_json['properties']['periods'][:12]]
    temperatures = [str(x["temperature"]) for x in response_json['properties']['periods'][:12]]
    humidities = [str(x['relativeHumidity']['value']) for x in response_json['properties']['periods'][:12]]
    wind_speeds = [x['windSpeed'] for x in response_json['properties']['periods'][:12]]
    short_forecasts = [x['shortForecast'] for x in response_json['properties']['periods'][:12]]


    # Create a grid layout with the header row
    md_table += ("| Time | Temperature (F) | Humidity (%) | Wind Speed (mph) | Short Forecast |\n")
    md_table += ("| --- | --- | --- | --- | --- |\n")

    # Display data in each row
    for i in range(12):
        md_table += f"| {times[i]} | {temperatures[i]} | {humidities[i]} | {wind_speeds[i]} | {short_forecasts[i]} |\n"
    return md_table
def main():
    st.set_page_config(
        page_icon="🏃"
    )

    state_vars = ['running_graph', 'address_coords', 'sub', 'source', 'sink', 'length_running', 'route', 'running_route_results', 'route_iter']

    for var in state_vars:
        if var not in st.session_state:
            st.session_state[var] = None

    st.subheader("Running Routes")

    #widget inputs
    with st.sidebar:
        st.subheader("Optimization Preferences")

        st.radio("Grade Preference", ["Flat","Steep"],key="elevation_type")
        st.radio("Turn Preference", ["Many Turns","Few Turns"],key="turn_type")
        st.write("Greenways, sidewalks, and other pedestrian-friendly paths are preferred by default. ")


    map_mode = st.toggle("Select Start Location Via Map", key="select_map")

    address = None
    location = get_geolocation()
    if location is not None:
        if map_mode:

            m = folium.Map(location=[location["coords"]["latitude"],location["coords"]["longitude"]],zoom_start=15,tiles=config.running_opts["map_tile"], attr=config.running_opts["map_tile_attr"])

            folium.LatLngPopup().add_to(m)
            user_location_input = streamlit_folium.st_folium(m)

            if user_location_input["last_clicked"] != None:
                address = [user_location_input["last_clicked"]["lat"],user_location_input["last_clicked"]["lng"]]
                folium.Marker(address).add_to(m)
        else:
            @st.cache_data()
            def get_add():
                default_add = geocode.pelias_reverse(client, [location["coords"]["longitude"],location["coords"]["latitude"]])
                default_add = default_add["features"][0]["properties"]["label"]
                return default_add


            address = streamlit_searchbox.st_searchbox(label="Address of Start Location",search_function=pelias_autocomplete, placeholder=get_add(), default=get_add())

        #test folium entry
        st.number_input("Desired Mileage", value=3, key="mileage")
        #run  model
        st.button("Generate Routes",on_click=build_cache_support,args=[address, map_mode])

    if st.session_state["running_route_results"] is not None:
        def route_plus():
            if st.session_state["route_iter"] < st.session_state["route_iter_max"] - 1:
                st.session_state["route_iter"] +=1
            else:
                st.toast("This is the last generated route. Press the left arrow to see other routes. ")

        def route_minus():
            if st.session_state["route_iter"] > 0:
                st.session_state["route_iter"] -= 1
            else:
                st.toast("This is the first generated route. Press the right arrow to see other routes. ")

        #begin map layout
        cola, colb, colc = st.columns([1,10,1])
        cola.button(label=":arrow_backward:", on_click=route_minus)
        colc.button(label=":arrow_forward:", on_click=route_plus)

        sub = st.session_state["running_route_results"][st.session_state["route_iter"]][0]
        map_location = st.container()

        route = st.session_state["running_route_results"][st.session_state["route_iter"]][5]
        nodes, edges = osmnx.graph_to_gdfs(sub, nodes=True, node_geometry=True)

        #out and back, reverse shortest path nodes list and append
        route_2 = route.copy()
        route_2.reverse()
        route = route + route_2
        route_nodes = nodes.loc[route]

        route_line = LineString([(point.x, point.y, point.elevation) for point in route_nodes.itertuples()])

        gdf1 = geopandas.GeoDataFrame(geometry=[route_line], crs=osmnx.settings.default_crs)
        #check to ensure no length/origin parameter changes
        if str(gdf1["geometry"][0]) != "LINESTRING EMPTY":
            elevation = route_nodes['elevation'].values*3.28084

            # Calculate cumulative distance
            distances = [0]
            for i in range(0, len(route)-1):
                try:
                    distances.append(st.session_state["running_graph"].edges[route[i],route[i+1],0]["length"]/1609.34+distances[-1])
                except:
                    distances.append(distances[-1]+0)
            # Plot elevation over distance using fig, ax style
            fig, ax = plt.subplots(figsize=(7,4))
            ax.plot(distances, elevation, marker='o', linestyle='-')
            ax.set_xlabel('Distance (mi) ')
            ax.set_ylabel('Elevation (ft)')
            ax.set_title('Elevation')
            ax.fill_between(distances, elevation, color='skyblue', alpha=0.4)
            ax.set_ylim(min(elevation))

            ax.grid(True)

            st.pyplot(fig)
            st.write(f'Total Distance Out and Back: {np.round(st.session_state["running_route_results"][st.session_state["route_iter"]][4]/1609.34,2)} mi') #meter to mile conversion
            st.write(f"**Elevation Cost**: {round(st.session_state['running_route_results'][st.session_state['route_iter']][3][0],2)}")
            st.write(f"**Turn Cost**: {round(st.session_state['running_route_results'][st.session_state['route_iter']][3][1],2)}")
            st.write(f"**Type Cost**: {round(st.session_state['running_route_results'][st.session_state['route_iter']][3][2],2)}")
        ##GPX Download


            file_mem = BytesIO()
            gdf1.to_file(file_mem,'GPX')

            st.download_button(label='Download GPX',file_name=config.running_opts["gpx_file_name"],mime="application/gpx+xml",data=file_mem, key="gpx_file")

            with map_location:
                with colb:
                    m = folium.Map(location=[gdf1.geometry.iloc[0].coords[0][1],gdf1.geometry.iloc[0].coords[0][0]], zoom_start=14, tiles=config.running_opts["map_tile"], attr=config.running_opts["map_tile_attr"])
                    folium.GeoJson(gdf1).add_to(m)
                    folium.Marker(location=[gdf1.geometry.iloc[0].coords[0][1],gdf1.geometry.iloc[0].coords[0][0]],
                                  tooltip=address).add_to(m)
                    streamlit_folium.st_folium(m, height=700, width=700)

            with st.expander("Weather"):
                st.markdown(nws_api())

if __name__ == "__main__":
    main()
