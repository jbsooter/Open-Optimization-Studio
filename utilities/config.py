#this file is used as a central location to set non-secret configuration parameters.
#for API-keys and other "secret" info, follow the local deployment instructions and create a secrets.toml file at .streamlit/secrets.toml
from calendar_view.core.event import EventStyles

#global options
solver_backend = dict(
    linear = "GLOP",
    mip = "CP_SAT",
    constraint = "CP_SAT"
    #These Solvers are free and open source for commerical use. They are developed and supported by Google's Operations Research group.
    #SCIP can be used for mip and linear for academic purposes only.
)

#Linear Programming module options
#color options for 2-var visualization
#options: any recognized colors from matplotlib
two_var_color_defaults = dict(
    infeasible = 'white',
    feasible = 'lightgreen',
    contour = 'darkgreen',
    gradient  = 'blue'
)

#Vehicle Routing options

#types of route profiles available for each service. For details on specific implementation, see Mapbox or ORS docs
provider_specific_profile_opts = dict(
    Mapbox = ['driving','walking','cycling','driving-traffic'],
    ORS = ['driving-car','foot-walking','cycling-regular']
)

vrp_opts = dict(
    matrix_provider = 'Mapbox', #options [Mapbox,ORS]
    matrix_server = 'Default', #options [Default,Local]
    matrix_profile_opts = provider_specific_profile_opts["Mapbox"], #pass through parameters that depend on matrix_provider
    geocoding_provider = 'ORS', #currently only option, others will be implemented in future
    folium_colors = [
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
] #colors to rotate through for tours. these are all possible
)


#Scheduling options
scheduling_opts = dict(

)

#Network Options
network_flows_opts = dict(

)

#Knapsack Options
knapsack_opts = dict(

)

#Time Blocking module options
calendar_opts = dict (
    lang='en',
    title='Task Schedule',
    show_date=True,
    legend=False,
    title_vertical_align='top'
)

calendar_event_opts = dict(
    event_display_color = EventStyles.GREEN,
    task_display_color = EventStyles.BLUE
)







