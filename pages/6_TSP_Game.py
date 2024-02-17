import math

import folium
import gspread
import pandas as pd
import streamlit as st
from folium.plugins import Draw

from streamlit_folium import st_folium
from geopy.distance import geodesic

st.set_page_config(layout='wide')

instance_b = {
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

instance_a = {
    "Little Rock": (34.7465, -92.2896),
    "Fort Smith": (35.3859, -94.3985),
    "Fayetteville": (36.0822, -94.1719),
    "Springdale": (36.1867, -94.1288),
    "Jonesboro": (35.8423, -90.7043),
    #"North Little Rock": (34.7695, -92.2608),
    "Conway": (35.0887, -92.4421),
    "Rogers": (36.332, -94.1185),
    "Bentonville": (36.3728, -94.2088),
    "Pine Bluff": (34.224, -92.0198),
    "Benton": (34.5645, -92.5868),
    "Hot Springs": (34.5037, -93.0552),
    #"Sherwood": (34.8151, -92.2243),
    "Texarkana": (33.4251, -94.0477),
    "Russellville": (35.2784, -93.1338),
    #"Jacksonville": (34.8668, -92.1111),
    "Bella Vista": (36.4814, -94.273),
    "Paragould": (36.058, -90.5132),
    "Cabot": (34.9745, -92.0165),
    "West Memphis": (35.1465, -90.1848),
    "Searcy": (35.2506, -91.7362),
    "Van Buren": (35.4362, -94.3483),
    "El Dorado": (33.2076, -92.6663),
    "Bryant": (34.6105, -92.4895),
    "Maumelle": (34.8676, -92.4003),
    "Siloam Springs": (36.1881, -94.5405),
    "Blytheville": (35.9273, -89.9187),
    "Forrest City": (35.0081, -90.7898),
    "Harrison": (36.2296, -93.1077)
}



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
    if "leaderboard" not in st.session_state:
        st.session_state["leaderboard"] = None
        read_scores()
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

            for i in range(0, len(output["all_drawings"][0]["geometry"]["coordinates"])-1):

                    a = output["all_drawings"][0]["geometry"]["coordinates"][i]
                    b = output["all_drawings"][0]["geometry"]["coordinates"][i+1]

                    total_distance += geodesic((a[1],a[0]),(b[1],b[0])).miles

            polylines_only.append(output["all_drawings"][0]["geometry"])

            st.write("Total Distance (mi):   " + str(round(total_distance,3)))

            val = validate_tsp_solution(polylines_only, instance_a)
            st.write(val[1])
            st.button("Submit Score",on_click=write_scores, args=[name, total_distance,val])

            with st.sidebar:
                st.dataframe(st.session_state["leaderboard"])



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

    leaders = pd.DataFrame(scoreboard.get_all_records())
    leaders = leaders.drop(leaders[(leaders == 0).any(axis=1)].index)
    st.session_state["leaderboard"]= leaders


if __name__ == "__main__":
    main()