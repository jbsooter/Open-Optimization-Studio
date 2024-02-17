import math

import folium
import gspread
import pandas as pd
import streamlit as st
from folium.plugins import Draw

from streamlit_folium import st_folium
from geopy.distance import geodesic

st.set_page_config(layout='wide')

instance_a = {
    "Little Rock, Arkansas": (34.7465, -92.2896),
    "Fayetteville, Arkansas": (36.0626, -94.1574),
    "Fort Smith, Arkansas": (35.3872, -94.4244),
    "Jonesboro, Arkansas": (35.8423, -90.7043),
    "Springfield, Missouri": (37.2083, -93.2923),
    "Kansas City, Missouri": (39.0997, -94.5786),
    "St. Louis, Missouri": (38.6270, -90.1994),
    "Tulsa, Oklahoma": (36.1540, -95.9928),
    "Oklahoma City, Oklahoma": (35.4676, -97.5164),
    "Wichita, Kansas": (37.6872, -97.3301),
    "Topeka, Kansas": (39.0473, -95.6752)
}


def validate_tsp_solution(polylines, cities):
    """Validate if the given set of polylines is a solution to the TSP for the given cities."""
    path = []
    for city in cities.values():
        incCount = 0

        for ltlng in polylines[0]["coordinates"][:-1]:

            if math.isclose(ltlng[0], city[1], abs_tol=0.05)&math.isclose(ltlng[1], city[0], abs_tol=0.05):
                incCount += 1
        if incCount == 1:
            path.append(city)



    if len(path) == len(cities):
        return [True, "Valid Solution"]
    else:
        return [False, "Infeasible Solution. Must Visit All Cities Once and Only Once. "]
def main():
    with st.sidebar:
        name = st.text_input("Team Name")

    m = folium.Map(location=[36.082157, -94.171852], zoom_start=5) #fayetteville
    for city, coord in instance_a.items():
        folium.Circle(location=coord, popup=city, radius=5000).add_to(m)
    Draw(export=True).add_to(m)

    output = st_folium(m, width=1300, height=1000)

    total_distance = 0

    polylines_only = []
    if output["all_drawings"] is not None:
        if len(output["all_drawings"]) != 0:
            polylines_only = []
            for x in output["all_drawings"]:
                #st.write(output["all_drawings"])
                if x["geometry"]["type"] == "LineString":
                    a = x["geometry"]["coordinates"][0]
                    #a.reverse()
                    b = x["geometry"]["coordinates"][1]
                    #b.reverse()
                    total_distance += geodesic((a[1],a[0]),(b[1],b[0])).miles
                    polylines_only.append(x["geometry"])

            st.write("Total Distance (mi):   " + str(round(total_distance,3)))

            val = validate_tsp_solution(polylines_only, instance_a)
            st.write(val[1])
            st.button("Submit Score",on_click=write_scores, args=[name, total_distance,val])




def write_scores(name, total_distance, val):
    if val[0]:
        gc = gspread.service_account_from_dict(st.secrets["google_sheets"])

        scoreboard = gc.open("TSP").worksheet("Scores")

        scoreboard.append_row([name, total_distance])
        scoreboard.sort((2,'asc'))
    else:
        st.write(val[1])
    read_scores()


def read_scores():
    gc = gspread.service_account_from_dict(st.secrets["google_sheets"])
    scoreboard = gc.open("TSP").worksheet("Scores")
    with st.sidebar:
        leaders = pd.DataFrame(scoreboard.get_all_records())
        leaders = leaders.drop(leaders[(leaders == 0).any(axis=1)].index)
        st.dataframe(leaders)


if __name__ == "__main__":
    main()