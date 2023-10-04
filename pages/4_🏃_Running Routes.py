import random

import geopandas
import numpy as np
import openrouteservice
import osmnx as osmnx
import streamlit as st
import streamlit_folium
import altair as alt
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
    st.session_state["running_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=1.3*st.session_state["mileage"]*1609/2, dist_type='network',network_type="all",
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,
                                                             clean_periphery=True)
    #snippet to add elevation to entire graph.
    osmnx.elevation.add_node_elevations_google(st.session_state["running_graph"],None,
                                               #url_template="https://api.opentopodata.org/v1/aster30m?locations={}&key={}",
                                               url_template = "https://api.open-elevation.com/api/v1/lookup?locations={}",
                                               max_locations_per_batch=150)

    st.session_state["running_boundary_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=(1.2*st.session_state["mileage"])*1609/2, dist_type='network',network_type="all",
                                                                                                     simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,

                                                                                             clean_periphery=True)
    build_route()

def cost_function(way,start_node,end_node):
    #https://taginfo.openstreetmap.org/keys
    cost = 100

    #if length is less than 500 metres, penalize to reduce tons of turns
    #if "length" in way:
    #    if int(way["length"]) < 500:
    #        cost = cost + 25
    #if speed limit is < 30 mph, make cheaper, if > 60 mph, make expensive
    if "maxspeed" in way:
        if int(way["maxspeed"][:2]) < 30:
            cost = cost - 10
        if int(way["maxspeed"][:2]) > 50:
            cost = cost + 10
    else: #some side roads have no value
        cost = cost -10
    #avoid raods
    if "highway" in way:
        if way["highway"] in ["primary","motorway","primary_link"]:
            cost = cost + 25
        if way["highway"] in ["service"]:
            cost = cost + 10
        #prefer cycleways
        if way["highway"]  in ["cycleway","track","residential","footway","tertiary"]:
            cost = cost - 25
    #make expensive if not designated foot
    if "foot" in way:
        if way["foot"] not in ["designated","yes"]:
            cost = cost + 10

    #corresponding cost logic if you were to explicitly consider elevation in min cost flow
    if "elevation" in start_node:
        if "elevation" in end_node:
            #st.write(np.absolute ((end_node["elevation"] - start_node["elevation"])/way["length"]))

            cost = cost - 100*np.sqrt(np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"]))
            #if(np.absolute ((end_node["elevation"] - start_node["elevation"])/way["length"]) > .025):
            #    cost = cost + 10
    #if "lit" in start_node:
    #    if start_node["lit"] == "yes":
    #        cost = cost - 100

    return cost*way["length"]

def build_route():
    results = []
    for i in range(0,10):
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
            cost = cost_function(data,st.session_state["running_graph"].nodes(data=True)[u],st.session_state["running_graph"].nodes(data=True)[v])  # or any other cost function
            #cost = cost_func_flat(data,st.session_state["running_graph"].nodes(data=True)[u],st.session_state["running_graph"].nodes(data=True)[v])  # or any other cost function
            capacity = 1  # arc only used once

            #add arc info and set supply 0
            run_mincostflow.add_arc_with_capacity_and_unit_cost(i_iter, j_iter, capacity, int(cost))
            run_mincostflow.set_node_supply(i_iter,0)
            run_mincostflow.set_node_supply(j_iter,0)

        # set source and sink
        source_return = osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])
        run_mincostflow.set_node_supply( u_i.get(source_return),1)

        #get node ids that are on the last graph 1-mi of the considered area
        result = [i for i in st.session_state["running_graph"] if i not in st.session_state["running_boundary_graph"]]

        #base sink on elevation. Find the greater absolute elevation difference nodes from nboundary region, take the top 10, and randomly select one of them for min cost flow
        current_max_elev =  0
        sink_return = {}

        #add values to node id keys that are the elevation delta (not grade) between source and current node
        for x in result:
            sink_return[x] = np.absolute(st.session_state["running_graph"].nodes()[x]["elevation"] - st.session_state["running_graph"].nodes()[source_return]["elevation"])

        #sort by elevation
        sink_return = dict(sorted(sink_return.items(), key=lambda item: item[1],reverse=True))

        #select from last 100
        sink_selected = random.choice(list(sink_return.keys()))

        #set sink to the selected
        run_mincostflow.set_node_supply(u_i.get(sink_selected),-1) #far away place

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
            results.append([sub,source_return,sink_selected,total_cost])

        results.sort(key = lambda row: row[3])
        st.session_state["sub"] = results[0][0]
        st.session_state["source"] = results[0][1]
        st.session_state["sink"] = results[0][2]

        #return results[0][:3]
def main():
    #initialize locaiton in session state
    if 'running_graph' not in st.session_state:
        st.session_state['running_graph'] = None

    if 'address_coords' not in st.session_state:
        st.session_state['address_coords'] = None

    if 'sub' not in st.session_state:
        st.session_state['sub'] = None

    if 'source' not in st.session_state:
        st.session_state['source'] = None

    if 'sink' not in st.session_state:
        st.session_state['sink'] = None

    st.subheader("Running Routes")

    address = streamlit_searchbox.st_searchbox(search_function=pelias_autocomplete)
    st.number_input("Desired Mileage", value=3, key="mileage")
    #run  model
    st.button("Go!",on_click=build_graph,args=[address])

    if st.session_state["sub"] is not None:
        sub = st.session_state["sub"]
        source = st.session_state["source"]
        sink = st.session_state["sink"]
        map_location = st.container()

        total_length = 10000000000
        route = []

        while total_length/1609.34 > 1.0000001*st.session_state["mileage"]:
            total_length_old = total_length
            route_old = route
            sub_old = sub
            total_length = 0

            route = osmnx.shortest_path(sub,source, sink)
            sub = sub.subgraph(route)

            for u,v,  key, edge_data in sub.edges(keys=True, data=True):
                total_length += edge_data['length']

            if(total_length/1609.34 < st.session_state["mileage"]):
                route = route_old
                total_length = total_length_old
                sub = sub_old
                break
            else:
                sink = route[-2]


        st.write(f'Total Distance Out and Back: {np.round(total_length/1609.34,2)}') #meter to mile conversion


        nodes, edges = osmnx.graph_to_gdfs(sub)

        #out and back, reverse shortest path nodes list and append
        route_2 = route.copy()
        route_2.reverse()
        route = route + route_2
        route_nodes = nodes.loc[route]

        route_line = LineString(route_nodes['geometry'].tolist())
        gdf1 = geopandas.GeoDataFrame(geometry=[route_line], crs=osmnx.settings.default_crs)

        #route_nodes['cumulative distance'] = cumulative_length
        #route_nodes = route_nodes.reset_index()
        #route_nodes = route_nodes.reset_index()
        #st.altair_chart(
        #    alt.Chart(route_nodes[["cumulative distance","elevation"]]).mark_line().encode(
        #    x=alt.X('cumulative distance',scale=alt.Scale(domain=[min(route_nodes["cumulative distance"]),max(route_nodes["cumulative distance"])])),
         #   y=alt.Y('elevation',scale=alt.Scale(domain=[min(route_nodes["elevation"]),max(route_nodes["elevation"])]))
       # )
        #)
        with map_location:
            col1,col2 = st.columns([2,1])
            with col1:
                streamlit_folium.st_folium(gdf1.explore(tooltip=True,tiles="Stamen Terrain",style_kwds={"weight":6}), returned_objects=[],height=700,width=700)
            col2.button(label="Regenerate Route", on_click=build_route)
        #GPX Download
        file_mem = BytesIO()
        gdf1.to_file(file_mem,'GPX')
        st.download_button(label='Download GPX',file_name="Route.gpx",mime="application/gpx+xml",data=file_mem)


if __name__ == "__main__":
    main()
