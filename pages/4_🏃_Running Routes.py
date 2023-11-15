import random
import geopandas
import numpy as np
import openrouteservice
import osmnx as osmnx
import streamlit as st
import streamlit_folium
import folium
import streamlit_searchbox

from openrouteservice import geocode
from shapely import LineString
from io import BytesIO

from streamlit_js_eval import get_geolocation

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

def build_graph(address,map_mode):
    with st.spinner(text="Requesting Map Data"):
        if map_mode == True:
            st.session_state["running_graph"] = osmnx.graph_from_point(address, dist=1.3*st.session_state["mileage"]*1609.34/2, dist_type='network',network_type=config.running_opts["osmnx_network_type"],
                                                                                                             simplify=False, retain_all=False, truncate_by_edge=False)
            st.session_state["address_coords"] = address

            st.session_state["running_boundary_graph"] = osmnx.graph_from_point(address, dist=(1.2*st.session_state["mileage"])*1609.34/2, dist_type='network',network_type=config.running_opts["osmnx_network_type"],
                                                                                                                  simplify=False, retain_all=False, truncate_by_edge=False)
            st.session_state["select_map"] = False
        else:
            # query osm
            st.session_state["running_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=1.3*st.session_state["mileage"]*1609.34/2, dist_type='network',network_type=config.running_opts["osmnx_network_type"],
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True)
            st.session_state["running_boundary_graph"] = osmnx.graph_from_address(address, dist=(1.2*st.session_state["mileage"])*1609.34/2, dist_type='network',network_type=config.running_opts["osmnx_network_type"],
                                                                                simplify=False, retain_all=False, truncate_by_edge=False, return_coords=False)
    with st.spinner(text="Requesting Elevation Data"):
        #snippet to add elevation to entire graph.
        osmnx.elevation.add_node_elevations_google(st.session_state["running_graph"],None,
                                               url_template = "https://api.open-elevation.com/api/v1/lookup?locations={}")
    build_route()

def cost_function(way,start_node,end_node):
    #https://taginfo.openstreetmap.org/keys
    cost = 1000

    #if length is less than 500 metres, penalize to reduce tons of turns
    if "length" in way:
        if int(way["length"]) < 500:
            cost = cost + 500
        elif int(way["length"]) < 1000:
            cost = cost + 200
        elif int(way["length"]) < 1500:
            cost = cost + 100

    #if speed limit is < 30 mph, make cheaper, if > 60 mph, make expensive
    if "maxspeed" in way:
        if int(way["maxspeed"][:2]) < 30:
            cost = cost - 250
        if int(way["maxspeed"][:2]) > 50:
            cost = cost + 750
    else: #some side roads have no value
        cost = cost - 10
    #avoid raods
    if "highway" in way:
        if way["highway"] in ["primary","motorway","primary_link"]:
            cost = cost + 500
        if way["highway"] in ["service","residential","unclassified"]:
            cost = cost + 300
        #prefer cycleways
        if way["highway"]  in ["cycleway","pedestrian","track","footway","tertiary","path","crossing"]:
            cost = cost - 500
    #make expensive if not designated foot
    if "foot" in way:
        #if way["foot"] not in ["designated","yes"]:
        cost = cost - 500

    #add 100x grade to cost per way
    if "elevation" in start_node:
        if "elevation" in end_node:
            cost = cost + 100*np.absolute((end_node["elevation"] - start_node["elevation"])/way["length"])

    #No negative costs
    if cost*way['length'] <= 0:
        return 0
    else:
        return cost*way["length"]

def build_route():
    #test shortest path only
    results = []
    for i in range(0,config.running_opts["out_back_node_n"]):
        for u, v, data in st.session_state["running_graph"].edges(data=True):
            data["cost"] = cost_function(data,st.session_state["running_graph"].nodes(data=True)[u],st.session_state["running_graph"].nodes(data=True)[v])

        # set source and sink
        source_return = osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])

        #get node ids that are on the last graph 1-mi of the considered area
        result = [i for i in st.session_state["running_graph"] if i not in st.session_state["running_boundary_graph"]]

        sink_selected = random.choice(result)

        route = osmnx.shortest_path(st.session_state["running_graph"],source_return, sink_selected, weight="cost")

        sub = st.session_state["running_graph"].subgraph(route)

        total_cost = 0
        for u,v,  key, edge_data in sub.edges(keys=True, data=True):
            total_cost += edge_data['cost']
        results.append([sub,source_return,sink_selected,total_cost])


    results.sort(key = lambda row: row[3])
    st.session_state["sub"] = results[0][0]
    st.session_state["source"] = results[0][1]
    st.session_state["sink"] = results[0][2]

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
    if 'uli' not in st.session_state:
        st.session_state['uli'] = None

    st.subheader("Running Routes")

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

    if st.session_state["sub"] is not None:
        sub = st.session_state["sub"]
        source = st.session_state["source"]
        sink = st.session_state["sink"]
        map_location = st.container()

        total_length = 0
        route = osmnx.shortest_path(sub,source, sink)

        for u,v,  key, edge_data in sub.edges(keys=True, data=True):
            total_length += edge_data['length']*2.0

        while total_length/1609.34 > 1.001*st.session_state["mileage"]:
            total_length_old = total_length
            route_old = route
            sub_old = sub
            total_length = 0

            route = osmnx.shortest_path(sub,source, sink)
            sub = sub.subgraph(route)

            for u,v,  key, edge_data in sub.edges(keys=True, data=True):
                total_length += edge_data['length']

            if((total_length)/1609.34 < st.session_state["mileage"]):
                route = route_old
                total_length = total_length_old
                sub = sub_old
                break
            else:
                sink = route[-2] #last becomes previous second to last


        nodes, edges = osmnx.graph_to_gdfs(sub)

        #out and back, reverse shortest path nodes list and append
        route_2 = route.copy()
        route_2.reverse()
        route = route + route_2
        route_nodes = nodes.loc[route]

        route_line = LineString(route_nodes['geometry'].tolist())

        gdf1 = geopandas.GeoDataFrame(geometry=[route_line], crs=osmnx.settings.default_crs)

        #check to ensure no length/origin parameter changes
        if str(gdf1["geometry"][0]) != "LINESTRING EMPTY":
            st.write(f'Total Distance Out and Back: {np.round(total_length/1609.34,2)}') #meter to mile conversion
            with map_location:
                col1,col2 = st.columns([2,1])
                with col1:
                    streamlit_folium.st_folium(gdf1.explore(tooltip=True,tiles=config.running_opts["map_tile"],attr=config.running_opts["map_tile_attr"],style_kwds={"weight":6}), returned_objects=[],height=700,width=700)
                col2.button(label="Regenerate Route", on_click=build_route)
            #GPX Download
            file_mem = BytesIO()
            gdf1.to_file(file_mem,'GPX')
            st.download_button(label='Download GPX',file_name=config.running_opts["gpx_file_name"],mime="application/gpx+xml",data=file_mem)


if __name__ == "__main__":
    main()
