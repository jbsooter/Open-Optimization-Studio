import random

import geopandas
import numpy as np
import openrouteservice
import osmnx as osmnx
import requests
import streamlit as st
import streamlit_folium
from io import BytesIO
from openrouteservice import geocode

import streamlit_searchbox
from ortools.graph.python import min_cost_flow
from shapely import LineString

from utilities import config

#useful tag config
osmnx.settings.useful_tags_way=['bridge', 'tunnel', 'oneway', 'lanes', 'ref', 'name',
                                 'highway', 'maxspeed', 'service', 'access', 'area',
                                 'landuse', 'width', 'est_width', 'junction', 'surface','length','foot']

osmnx.settings.useful_tags_node = ['name','lit','amenity']


#retrieve client
# ORS client to be shared among all methods
client = None
if config.vrp_opts["ors_server"] == "Default":
    client = openrouteservice.Client(key=st.secrets["ors_key"])
elif config.vrp_opts["ors_server"] == "Default-Personal":
    client = openrouteservice.Client(key=st.session_state["personal-ors-key"])
else:
    client = openrouteservice.Client(
        key=st.secrets["ors_key"],
        base_url=config.vrp_opts["ors_server"])


@st.cache_data(ttl= 2,show_spinner=False)
def pelias_autocomplete(searchterm: str) -> list[any]:
    #https://github.com/pelias/documentation/blob/master/autocomplete.md
    return [name["properties"]["label"] for name in geocode.pelias_autocomplete(client=client, text=searchterm,country="USA")["features"]]
def build_graph(address):
    # query osm
    st.session_state["running_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=st.session_state["mileage"]*1609/2, dist_type='network',network_type="all",
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,
                                                             clean_periphery=True)
    #snippet to add elevation to entire graph. this would allow for explicit consideration of grade in the min cost flow problem. This is somewhat computationally expensive on the
    #open source elevation APIs, which is not preferable. Currently accounting for elevation by guiding the sink node selection with elevation change from origin.
    #elevation from open topo data
    #osmnx.elevation.add_node_elevations_google(st.session_state["running_graph"],None,
    #                                           #url_template="https://api.opentopodata.org/v1/aster30m?locations={}&key={}",
    #                                           url_template = "https://api.open-elevation.com/api/v1/lookup?locations={}",
    #                                           max_locations_per_batch=150)

    st.session_state["running_boundary_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=(st.session_state["mileage"] - 1)*1609/2, dist_type='network',network_type="all",
                                                                                                     simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,
                                                                                                     clean_periphery=True)
def cost_function(way,start_node,end_node):
    cost = 10

    #if length is less than 500 metres, penalize to reduce tons of turns
    if "length" in way:
        if int(way["length"]) < 500:
            cost = cost + 1
    #if speed limit is < 30 mph, make cheaper, if > 60 mph, make expensive
    if "maxspeed" in way:
        if int(way["maxspeed"][:2]) < 30:
            cost = cost - 3
        if int(way["maxspeed"][:2]) > 60:
            cost = cost + 10

    #avoid raods
    if "highway" in way:
        if way["highway"] in [ "motorway","primary","service","residential","tertiary","service","primary_link","motorway"]:
            cost = cost +10
        #prefer cycleways
        if way["highway"]  in ["cycleway"]:
            cost = cost - 3
    #make expensive if not designated foot
    if "foot" in way:
        if way["foot"] not in ["designated"]:
            cost = cost + 10

    #corresponding cost logic if you were to explicitly consider elevation in min cost flow
    #if "elevation" in start_node:
    #    if(np.absolute (end_node["elevation"] - start_node["elevation"])/way["length"] ) > .04:
    #        cost = cost - 500


    return cost

def build_route():
    #solve
    run_mincostflow = min_cost_flow.SimpleMinCostFlow()
    # Define the cost and capacity for each edge
    #convert to zero based integer ortools
    i = 0
    u_i = {}
    i_u = {}
    for u, v, data in st.session_state["running_graph"].edges(data=True):
        #convert ids to unique integers
        i_iter = 0
        j_iter = 0
        if u in u_i:
            i_iter = u_i.get(u)
        else:
            i_iter = i
            u_i[u] = i
            i_u[i] = u
            i += 1

        if v in u_i:
            j_iter = u_i.get(v)
        else:
            j_iter = i
            u_i[v] = i
            i_u[i] = v
            i += 1

        #define cost
        cost = cost_function(data,st.session_state["running_graph"].nodes(data=True)[u],st.session_state["running_graph"].nodes(data=True)[u])  # or any other cost function
        capacity = 1  # arc only used once

        #add arc info and set supply 0
        run_mincostflow.add_arc_with_capacity_and_unit_cost(i_iter, j_iter, capacity, int(cost))
        run_mincostflow.set_node_supply(i_iter,0)
        run_mincostflow.set_node_supply(j_iter,0)

    # set source and sink
    source_return = osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])
    run_mincostflow.set_node_supply( u_i.get(source_return),1)
    result = [i for i in st.session_state["running_graph"] if i not in st.session_state["running_boundary_graph"]]

    #add elevation surgically to boundary nodes and source
    #build post request data for open-elevation.com for boundary region and source node
    post_data = {"locations":[]}
    post_data["locations"].append({"latitude": st.session_state["running_graph"].nodes()[source_return]["y"],"longitude":st.session_state["running_graph"].nodes()[source_return]["x"]})
    for x in result:
        post_data["locations"].append({"latitude": st.session_state["running_graph"].nodes()[x]["y"],"longitude":st.session_state["running_graph"].nodes()[x]["x"]})

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    #send requests and add to nodes
    response = requests.post("https://api.open-elevation.com/api/v1/lookup", headers=headers, json=post_data)

    st.session_state["running_graph"].nodes()[source_return]["elevation"] = response.json()["results"][0]["elevation"]
    resp_no_source = response.json()["results"][1:]

    i = 0
    for x in result:
        st.session_state["running_graph"].nodes()[x]["elevation"] = resp_no_source[i]["elevation"]
        i = i+1

    #base sink on elevation. Find the greater absolute elevation difference nodes from nboundary region, take the top 10, and randomly select one of them for min cost flow
    current_max_elev =  0
    sink_return = []
    for x in result:
        if np.absolute(st.session_state["running_graph"].nodes()[x]["elevation"] - st.session_state["running_graph"].nodes()[source_return]["elevation"]) > current_max_elev:
            sink_return.append(x)
            current_max_elev = np.absolute(st.session_state["running_graph"].nodes()[x]["elevation"]- st.session_state["running_graph"].nodes()[source_return]["elevation"])

    sink_return = random.choice(sink_return[-10:])
    run_mincostflow.set_node_supply(u_i.get(sink_return),-1) #far away place

    # Run the min cost flow algorithm
    if run_mincostflow.solve() == run_mincostflow.OPTIMAL:
        # Print the total cost and flow on each edge
        total_cost = run_mincostflow.optimal_cost()
        nodes_ij = []
        for w in range(run_mincostflow.num_arcs()):
            u = run_mincostflow.tail(w)
            v = run_mincostflow.head(w)
            flow = run_mincostflow.flow(w)
            cost = run_mincostflow.unit_cost(w)

            if flow > 0:
                #st.write(f'Edge ({u}, {v}): Flow = {flow}, Cost = {cost}')
                nodes_ij.append(i_u.get(u))
                nodes_ij.append(i_u.get(v))

        sub = st.session_state["running_graph"].subgraph(nodes_ij)


        return sub,source_return, sink_return
def main():
    user_entry = st.container()
    #initialize locaiton in session state
    if 'running_graph' not in st.session_state:
        st.session_state['running_graph'] = None


    if 'address_coords' not in st.session_state:
        st.session_state['address_coords'] = None

    st.subheader("Network Flows")

    address = streamlit_searchbox.st_searchbox(search_function=pelias_autocomplete, key="sl")
    st.number_input("Desired Mileage", value=3, key="mileage")
    #run  model
    st.button("Go!",on_click=build_graph,args=[address])

    sub = None
    source = None
    sink = None
    if st.session_state["running_graph"] is not None:
        sub,source, sink = build_route()

    if sub is not None:
        map_location = st.container()

        total_length = 0
        for u, v, key, edge_data in sub.edges(keys=True, data=True):
            total_length += edge_data['length']

        st.write(f'Total Distance Out and Back: {np.round( total_length/1609,2)}') #meter to mile conversion

        route = osmnx.shortest_path(sub,source, sink)
        nodes, edges = osmnx.graph_to_gdfs(sub)

        #out and back, reverse shortest path nodes list and append
        route_2 = route.copy()
        route_2.reverse()
        route = route + route_2
        route_nodes = nodes.loc[route]

        route_line = LineString(route_nodes['geometry'].tolist())
        gdf1 = geopandas.GeoDataFrame(geometry=[route_line], crs=osmnx.settings.default_crs)

        with map_location:
            streamlit_folium.st_folium(gdf1.explore(tooltip=True,tiles="Stamen Terrain",style_kwds={"weight":6}), returned_objects=[])
        gdf1.to_file('route1.gpx',"GPX")
        #GPX Download
        file_mem = BytesIO()
        gdf1.to_file(file_mem,'GPX')
        st.download_button(label='Download GPX',file_name="Route.gpx",mime="application/gpx+xml",data=file_mem)
        st.button(label="Regenerate Route", on_click=build_route)

if __name__ == "__main__":
    main()
