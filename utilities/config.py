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
    osmnx_network_filters = ["""["highway" ~ "footway|sidewalk|footpath|path|residential|pedestrian|crossing|service|cycleway|track"]""","""["foot" ~ "designated|yes"]"""]

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
