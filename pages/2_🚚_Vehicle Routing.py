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
        matrix = client.matrix(locations=nodes,profile="driving",annotations=[st.session_state["matrix_metric"]])
    elif config.vrp_opts["matrix_provider"] == 'ORS':
        client = ORS(api_key=st.secrets["matrix_key"])
        matrix = client.matrix(locations=nodes,profile="driving",metrics=[st.session_state["matrix_metric"]])

    if st.session_state["matrix_metric"] == 'distance':
        return matrix.distances
    else:
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

def main():
    st.write("Coming Soon!")
    st.selectbox(label="Traveller Profile",options=config.vrp_opts["matrix_profile_opts"],key='matrix_profile')
    st.selectbox(label = "Arc Cost Type",options=["distance","duration"],key="matrix_metric")
    #st.write(query_matrix([[ -94.110947,36.052985,],[ -94.122620,36.072967,]]))
    #st.write(geocode_addresses(["831 W Center Street Fayettville AR"]))

if __name__ == "__main__":
    main()