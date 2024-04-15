# this file is used as a central location to set non-secret configuration parameters.
# for API-keys and other "secret" info, follow the local deployment
# instructions and create a secrets.toml file at .streamlit/secrets.toml
from calendar_view.core.event import EventStyles

# global options
solver_backend = dict(
    linear="GLOP",
    mip="CP_SAT",
    constraint="CP_SAT"
    # These Solvers are free and open source for commerical use. They are developed and supported by Google's Operations Research group.
    # SCIP can be used for mip and linear for academic purposes only.
)

# Linear Programming module options
# color options for 2-var visualization
# options: any recognized colors from matplotlib
two_var_color_defaults = dict(
    infeasible='white',
    feasible='lightgreen',
    contour='darkgreen',
    gradient='blue'
)

# Vehicle Routing options
trip_planning_opts = dict(
    ors_server='Default',  # options [Default,insert/url/here]
    ors_matrix_profile_opts=['driving-car',
                             'foot-walking',
                             'cycling-regular',
                             'cycling-electric',
                             'cycling-mountain',
                             'cycling-road',
                             'driving-hgv',
                             'foot-hiking',
                             'wheelchair'],
    max_num_nodes=8,
    folium_colors=[
        'red',
        'blue',
        'gray',
        'darkred',
        'lightred',
        'orange',
        'beige',
        'green',
        'darkgreen',
        'lightgreen',
        'darkblue',
        'lightblue',
        'purple',
        'darkpurple',
        'pink',
        'cadetblue',
        'lightgray',
        'black'
    ] , # colors to rotate through for tours. these are all possible
    cost_metrics =
    ['distance','duration']
)


# Scheduling options
scheduling_opts = dict(

)

# Running Options
running_opts = dict(
    #http://leaflet-extras.github.io/leaflet-providers/preview/
    map_tile = 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    map_tile_attr = 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    gpx_file_name = "route.gpx",
    out_back_node_n = 10,
    osmnx_network_filters = ["""["highway" ~ "footway|sidewalk|footpath|path|residential|pedestrian|crossing|service|cycleway|track"]""","""["foot" ~ "designated|yes"]"""],
    max_iterations = 1000,
    acceptable_variance_from_best = 1,
    tabu_similarity_pct=0.5,
    tabu_list_length=10

)

# Knapsack Options
knapsack_opts = dict(
    default_data = {
    'Name': ['Backpack', 'Clothes (3 outfits)', 'Toiletries (small bag)', 'Travel adapter', 'Water bottle', 'Snacks and other consumables', 'Guidebook', 'Camera', 'Headphones', 'First-aid kit', 'Phone charger & portable battery', 'Miscellaneous (pens, sunglasses, etc.)'],
    'Size': [9, 6, 3, 2, 4, 5, 4, 6, 4, 3, 3, 2],
    'Value': [8, 7, 5, 4, 2, 6, 3, 8, 6, 4, 5, 3]
}
)

# Time Blocking module options
calendar_opts = dict(
    lang='en',
    title='Task Schedule',
    show_date=True,
    legend=False,
    title_vertical_align='top'
)

calendar_event_opts = dict(
    event_display_color=EventStyles.GREEN,
    task_display_color=EventStyles.BLUE
)

#TSP game opts
tsp_game_opts = dict(
    Arkansas={
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
    },
    South_Central={
    "University of Arkansas": (36.0679, -94.1737),  # Fayetteville, Arkansas
    "Oklahoma State University": (36.1322, -97.0681),  # Stillwater, Oklahoma
    "University of Oklahoma": (35.2080, -97.4458),  # Norman, Oklahoma
    "University of Tulsa": (36.1498, -95.9460),  # Tulsa, Oklahoma
    "Texas A&M University": (30.6212, -96.3402),  # College Station, Texas
    "University of Texas at Arlington": (32.7357, -97.1081),  # Arlington, Texas
    "Texas Tech University": (33.5844, -101.8807),  # Lubbock, Texas
    "University of Texas at El Paso": (31.7727, -106.5055),  # El Paso, Texas
    "University of Houston": (29.7199, -95.3422),  # Houston, Texas
    "University of Texas at Austin": (30.2849, -97.7341),  # Austin, Texas
    "Wichita State University": (37.7171, -97.2955),  # Wichita, Kansas
    "Missouri University of Science and Technology": (37.9515, -91.7713),  # Rolla, Missouri
    "University of Missouri": (38.9404, -92.3276)  # Columbia, Missouri
},
    Airports= {
    "Hartsfield-Jackson Atlanta International Airport": (33.6407, -84.4277),
    "Los Angeles International Airport": (33.9416, -118.4085),
    "Chicago O'Hare International Airport": (41.9796, -87.9045),
    "Dallas/Fort Worth International Airport": (32.8998, -97.0403),
    "Denver International Airport": (39.8561, -104.6737),
    "John F. Kennedy International Airport": (40.6413, -73.7781),
    "San Francisco International Airport": (37.6189, -122.3750),
    "Seattle-Tacoma International Airport": (47.4502, -122.3088),
    "Orlando International Airport": (28.4294, -81.3089),
    "Miami International Airport": (25.7959, -80.2870),
    "Phoenix Sky Harbor International Airport": (33.4373, -112.0078),
    "Charlotte Douglas International Airport": (35.2140, -80.9431),
    "George Bush Intercontinental Airport": (29.9902, -95.3368),
    "Newark Liberty International Airport": (40.6895, -74.1745),
    "McCarran International Airport": (36.0851, -115.1510),
    "Detroit Metropolitan Wayne County Airport": (42.2121, -83.3488),
    "Minneapolis-Saint Paul International Airport": (44.8810, -93.2218),
    "Logan International Airport": (42.3656, -71.0096),
    "Fort Lauderdale-Hollywood International Airport": (26.0722, -80.1528),
    "Philadelphia International Airport": (39.8721, -75.2421),
    "Salt Lake City International Airport": (40.7899, -111.9791),
    "LaGuardia Airport": (40.7769, -73.8740),
    "Baltimore/Washington International Thurgood Marshall Airport": (39.1774, -76.6684)
},
    NBA  = {
    "Los Angeles Lakers": (34.0522, -118.2437),
    "Golden State Warriors": (37.768, -122.3878),
    "Chicago Bulls": (41.8807, -87.6742),
    "Boston Celtics": (42.3662, -71.0621),
    "Miami Heat": (25.7814, -80.1881),
    #"New York Knicks": (40.7505, -73.9934),
    "Houston Rockets": (29.7508, -95.3621),
    "San Antonio Spurs": (29.4275, -98.4375),
    "Philadelphia 76ers": (39.9012, -75.1719),
    "Dallas Mavericks": (32.7903, -96.8103),
    "Toronto Raptors": (43.6435, -79.3791),
    "Portland Trail Blazers": (45.5316, -122.6663),
    "Brooklyn Nets": (40.6826, -73.9745),
    #"Los Angeles Clippers": (34.043, -118.2673),
    "Phoenix Suns": (33.4457, -112.0712),
    "Milwaukee Bucks": (43.0436, -87.9169),
    "Denver Nuggets": (39.7487, -105.0077),
    "Atlanta Hawks": (33.7573, -84.3963),
    "Indiana Pacers": (39.7639, -86.1555),
    "Washington Wizards": (38.8981, -77.0209),
    "Utah Jazz": (40.7683, -111.9011),
    "Memphis Grizzlies": (35.138, -90.0505),
    "New Orleans Pelicans": (29.9499, -90.0822),
    "Minnesota Timberwolves": (44.9795, -93.2761),
    "Orlando Magic": (28.5392, -81.3832),
    #"Sacramento Kings": (38.5802, -121.4994),
    "Detroit Pistons": (42.3411, -83.0554),
    "Charlotte Hornets": (35.2251, -80.8392),
    "Cleveland Cavaliers": (41.4966, -81.688),
    "Oklahoma City Thunder": (35.4634, -97.5151)
},
    Challenge_1962 = {
        "Lewiston": (46.4165, -117.0177),
        "Portland": (45.5051, -122.6750),
        "Boise": (43.6150, -116.2023),
        "Butte": (46.0038, -112.5348),
        "Twin Falls": (42.5622, -114.4609),
        "Redding": (40.5865, -122.3917),
        "Reno": (39.5296, -119.8138),
        "Gustine": (37.2545, -120.9996),
        "Lone Pine": (36.6060, -118.0629),
        "Salt Lake City": (40.7608, -111.8910),
        "Mexican Hat": (37.1721, -109.8477),
        "Marble Canyon": (36.8120, -111.6457),
        "Truth or Consequences": (33.1284, -107.2528),
        "Amarillo": (35.2211, -101.8313),
        "Wichita": (37.6872, -97.3301),
        "Lincoln": (40.8136, -96.7026),
        "Blunt": (44.1884, -99.9626),
        "Kansas City": (39.0997, -94.5786),
        "Little Rock": (34.7465, -92.2896),
        "Baton Rouge": (30.4515, -91.1871),
        "La Crosse": (43.8014, -91.2396),
        "Chicago": (41.8781, -87.6298),
        "Indianapolis": (39.7684, -86.1581),
        "Marion": (37.7306, -88.9331),
        "Erie": (42.1292, -80.0851),
        "Carlisle": (40.2010, -77.2003),
        "Wana": (39.6424, -79.9894),
        "Wilkesboro": (36.1525, -81.1575),
        "Chattanooga": (35.0456, -85.3097),
        "Barnwell": (33.2457, -81.3606),
        "Bainbridge": (30.9037, -84.5794)
    }
)
