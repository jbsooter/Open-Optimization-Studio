import datetime
import math
import random
import time

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

from openrouteservice import geocode
from shapely import LineString
from io import BytesIO

from shapely.ops import substring
from streamlit_js_eval import get_geolocation

from utilities import config

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

def build_graph(address,map_mode):
    with st.spinner(text="Requesting Map Data"):
        if map_mode == True:
            rgs = []
            rgs_b = []
            #combine all the filtered data thats requested
            for x in config.running_opts["osmnx_network_filters"]:
                rgs.append(osmnx.graph_from_point(address, dist=1.1*st.session_state["mileage"]*1609.34/2, dist_type='bbox',
                                                                                                             simplify=False, retain_all=False, truncate_by_edge=False,custom_filter=x))
                rgs_b.append(osmnx.graph_from_point(address, dist=(0.9*st.session_state["mileage"])*1609.34/2, dist_type='bbox',
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
                r_i, st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=1.1*st.session_state["mileage"]*1609.34/2, dist_type='bbox',
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,custom_filter=x, )
                rgs.append(r_i)
                rgs_b.append(osmnx.graph_from_address(address, dist=(0.9*st.session_state["mileage"])*1609.34/2, dist_type='bbox',
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
                    st.error("Open-Elevation.com appears to be experiencing downtime. Please try again later. ")

    build_route()

def cost_function(way,start_node,end_node):
    #all 100 to make easier to track weights
    turn_cost = 100
    speed_cost = 100
    elevation_cost = 50
    type_cost = 100
    #https://taginfo.openstreetmap.org/keys

    #if length is less than 500 metres, penalize to reduce tons of turns
    if "length" in way:
        if st.session_state["turn_penalty"] =="Linear":
            if st.session_state["turn_type"] == "Many Turns":
                if int(way["length"]) < 500:
                    turn_cost -= 100
                elif int(way["length"]) < 1000:
                    turn_cost -= 75
                elif int(way["length"]) < 1500:
                    turn_cost -= 50
            elif st.session_state["turn_type"] == "Few Turns":
                if int(way["length"]) < 500:
                    turn_cost += 100
                elif int(way["length"]) < 1000:
                    turn_cost += 75
                elif int(way["length"]) < 1500:
                    turn_cost += 50
        elif st.session_state["turn_penalty"] == "Exponential":
            if st.session_state["turn_type"] == "Many Turns":
                if int(way["length"]) < 500:
                    turn_cost -= math.pow(2,6)
                elif int(way["length"]) < 1000:
                    turn_cost -= math.pow(2,5)
                elif int(way["length"]) < 1500:
                    turn_cost -= math.pow(2,4)
            elif st.session_state["turn_type"] == "Few Turns":
                turn_cost = 0
                if int(way["length"]) < 500:
                    turn_cost += math.pow(2,6)
                elif int(way["length"]) < 1000:
                    turn_cost += math.pow(2,5)
                elif int(way["length"]) < 1500:
                    turn_cost += math.pow(2,4)
    #if speed limit is < 30 mph, make cheaper, if > 60 mph, make expensive
    if "maxspeed" in way:
        try:
            if int(way["maxspeed"][:2]) <= st.session_state["speed_restriction"]:
                speed_cost -= 100
        except TypeError:
            int()
    #avoid raods
    if "highway" in way:
        #if way["highway"] in ["primary","motorway","primary_link"]:
        #    type_cost += 100
        if way["highway"] in ["service","residential","unclassified", "tertiary"]:
            type_cost -= 50
        #prefer cycleways
        if st.session_state["greenway_preference"]:
            if way["highway"]  in ["cycleway","pedestrian","track","footway","path"]:
                type_cost  -= 100

            if "foot" in way:
                if way["foot"] in ["designated","yes"]:
                    type_cost = min(0, type_cost)

    #add 100x grade to cost per way
    if "elevation" in start_node:
        if "elevation" in end_node:
            if st.session_state["elevation_penalty"] == "Linear":
                if st.session_state["elevation_type"] == "Flat":
                    elevation_cost +=  200*np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"])
                elif st.session_state["elevation_type"] == "Steep":
                    elevation_cost -= 200*np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"])
            elif st.session_state["elevation_penalty"] == "Exponential":
                if st.session_state["elevation_type"] == "Flat":
                    elevation_cost += math.pow(2, min(5.6435,20*(np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"]))))
                elif st.session_state["elevation_type"] == "Steep":
                    elevation_cost -= math.pow(2, min(5.6435,20*(np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"]))))

    cost = (st.session_state["grade_weight"]*elevation_cost
            + st.session_state["turns_weight"]*turn_cost
            + st.session_state["road_type_weight"]*type_cost
            + st.session_state["speed_weight"]*speed_cost)

    return cost*way["length"] #more costly if lasts longer debating this

def build_route():
    with st.spinner("Computing Routes"):
        #test shortest path only
        results = []
        for u, v, data in st.session_state["running_graph"].edges(data=True):
            data["cost"] = cost_function(data,st.session_state["running_graph"].nodes(data=True)[u],st.session_state["running_graph"].nodes(data=True)[v])

            # set source and sink
        source_return = osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])

        #get node ids that are on the last graph 1-mi of the considered area
        rg_local = nx.MultiDiGraph(st.session_state["running_graph"])
        osmnx.simplify_graph(rg_local)

        rbg_local = nx.MultiDiGraph(st.session_state["running_boundary_graph"])
        osmnx.simplify_graph(rbg_local)
        result = [i for i in rg_local if i not in rbg_local]
        #guaruntee node uniwqueness
        result = set(result)
        result = list(result)
        #new seed based on time
        current_time = int(time.time())
        random.seed(current_time)
        z = -1
        z_same = 0
        z_prev = 0
        while z < st.session_state["routes_to_generate"]:
            #guaruntee against infinite loop
            if z_prev == z:
                z_same+= 1
            else:
                z_same = 0

            if z_same >= 100:
                break

            sink_selected = random.choice(result)
            result.remove(sink_selected)

            def sp(source_return, sink_selected):
                return  osmnx.shortest_path(st.session_state["running_graph"],source_return, sink_selected, weight="cost")

            #in case no route exists
            while True:
                route = sp(source_return, sink_selected)
                try:
                    len(route)
                    break
                except TypeError:
                    sink_selected = random.choice(result)
                    result.remove(sink_selected)

            sub = st.session_state["running_graph"].subgraph(route)

            total_length = 0
            total_cost = 0

            #cut the route down to exact mileage
            route_cut = []
            for i in range(0, len(route)-1):
                if total_length/1609.34 <= st.session_state["mileage"]:
                    u = route[i]
                    v = route[i + 1]
                    route_cut.append(u)

                    if sub.has_edge(u, v):
                        total_length += st.session_state["running_graph"][u][v][0]["length"]*2
                        total_cost += st.session_state["running_graph"][u][v][0]["cost"]

                else:
                    #route_cut.append(route[i-1])
                    total_length -= st.session_state["running_graph"][route[i-2]][route[i-1]][0]["length"]*2
                    break

            sub = sub.subgraph(route_cut)
            sink_selected = route_cut[-1]

            #post-hoc uniqueness
            subs_added = []
            for x in results:
                subs_added.append(x[2])

            if sink_selected not in subs_added:
                z_prev = z
                z+=1
                results.append([sub,source_return,sink_selected,total_cost, total_length, route_cut])
            else:
                z_prev = z


        results.sort(key = lambda row: row[3])

        #ensure uniqueness after cuts

        st.session_state["running_route_results"] = results
        st.session_state["route_iter"] = 0
        st.session_state["route_iter_max"] = z + 1

@st.cache_data(ttl=15*60) #refresh 15 min
def nws_api():
    #weather
    URL = f'https://api.weather.gov/points/{st.session_state["address_coords"][0]},{st.session_state["address_coords"][1]}'

    response = requests.get(URL)

    URL = response.json()['properties']['forecastHourly']
    response = requests.get(URL)

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
        col1, col2 = st.columns([1,1])
        with col1:
            st.radio("Grade Preference", ["Flat","Steep"],key="elevation_type")
            st.radio("Turn Preference", ["Many Turns","Few Turns"],key="turn_type")
            st.number_input("Avoid Roads with Speed Limit >", value=30,key="speed_restriction")

            st.slider("Grade Importance: ", min_value=0, max_value=100, value=25, key="grade_weight")
            st.slider("Turns Importance: ", min_value=0, max_value=100, value=25, key="turns_weight")
            st.number_input("Number of Routes to Generate", value=config.running_opts["out_back_node_n"], key="routes_to_generate")

        with col2:
            st.radio("Penalty",["Linear","Exponential"], key="elevation_penalty")
            st.radio("Penalty",["Linear","Exponential"], key="turn_penalty")
            st.toggle("Prefer Greenway", value=True,key="greenway_preference")

            for x in range(0,1):
                st.write(" ")
            st.slider("Road Type Importance: ", min_value=0, max_value=100, value=25, key="road_type_weight")
            st.slider("Speed Importance: ", min_value=0, max_value=100, value=25, key="speed_weight")

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
        st.button("Generate Routes",on_click=build_graph,args=[address, map_mode])

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
            st.write(f'Total Distance Out and Back: {np.round(st.session_state["running_route_results"][st.session_state["route_iter"]][4]/1609.34,2)}') #meter to mile conversion
            #GPX Download
            file_mem = BytesIO()
            gdf1.to_file(file_mem,'GPX')
            st.download_button(label='Download GPX',file_name=config.running_opts["gpx_file_name"],mime="application/gpx+xml",data=file_mem)

            with map_location:
                with colb:
                    m = folium.Map(location=[gdf1.geometry.iloc[0].coords[0][1],gdf1.geometry.iloc[0].coords[0][0]], zoom_start=15)
                    folium.GeoJson(gdf1).add_to(m)
                    folium.Marker(location=[gdf1.geometry.iloc[0].coords[0][1],gdf1.geometry.iloc[0].coords[0][0]],
                                  tooltip=address).add_to(m)
                    streamlit_folium.st_folium(m, height=700, width=700)

            with st.expander("Weather Report"):
                st.markdown(nws_api())

if __name__ == "__main__":
    main()
