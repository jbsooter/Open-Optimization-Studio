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
two_var_color_defaults = dict(
    infeasible = 'white',
    feasible = 'lightgreen',
    contour = 'darkgreen',
    gradient  = 'blue'
)

#Vehicle Routing options
vrp_opts = dict(

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







