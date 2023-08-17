import osmnx as osmnx
import streamlit as st
import streamlit_folium
from io import BytesIO
from ortools.graph.python import min_cost_flow

#useful tag config
osmnx.config(useful_tags_way=["highway","maxspeed","surface","access","amenity"])

def build_graph(address):
    # query osm
    st.session_state["running_graph"], st.session_state["address_coords"] = osmnx.graph_from_address(address, dist=st.session_state["mileage"]*1609, dist_type='network',network_type="walk",
                                                             simplify=False, retain_all=False, truncate_by_edge=False, return_coords=True,
                                                             clean_periphery=True)
def cost_function(highway,landuse,maxspeed):
    cost = 10
    if highway not in [ "motorway","primary","service"]:
        cost = cost -1
    if landuse in ["university"]:
        cost = cost - 5
    if int(maxspeed[:2]) < 30:
        cost = cost - 3
    return cost


def main():
    #initialize locaiton in session state
    if 'running_graph' not in st.session_state:
        st.session_state['running_graph'] = None


    if 'address_coords' not in st.session_state:
        st.session_state['address_coords'] = None

    st.subheader("Network Flows")

    
    #useful tag config
    osmnx.config(useful_tags_way=["highway","maxspeed","surface","access","amenity"])
    #get address and graph
    address = st.text_input(label="Start Location")

    st.number_input("Desired Mileage", value=3, key="mileage")
    #run  model
    st.button("Go!",on_click=build_graph,args=[address])

    if st.session_state['running_graph'] != None:
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
            #    st.write(data)
            lu = None
            ms = "100"
            if "amenity" in data:
                #st.write("hit")
                lu = data["amenity"]
            if "maxspeed" in data:
                ms = data["maxspeed"]
            cost = cost_function(data['highway'],lu,ms)  # or any other cost function
            capacity = 1  # arc only used once

            #add arc info and set supply 0
            run_mincostflow.add_arc_with_capacity_and_unit_cost(i_iter, j_iter, capacity, int(cost))
            run_mincostflow.set_node_supply(i_iter,0)
            run_mincostflow.set_node_supply(j_iter,0)

        # set source and sink

        run_mincostflow.set_node_supply( u_i.get(osmnx.nearest_nodes(st.session_state["running_graph"],st.session_state["address_coords"][1],st.session_state["address_coords"][0])),1)
        run_mincostflow.set_node_supply(i-1,-1) #far away place

        # Run the min cost flow algorithm
        #st.write(run_mincostflow.solve())
        if run_mincostflow.solve() == run_mincostflow.OPTIMAL:
            # Print the total cost and flow on each edge
            total_cost = run_mincostflow.optimal_cost()
            #st.write(total_cost)
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
    
            streamlit_folium.folium_static(osmnx.plot_graph_folium(sub))
    
            total_length = 0
            for u, v, key, edge_data in sub.edges(keys=True, data=True):
                total_length += edge_data['length']
    
            st.write(f'Total Distance Out and Back: { total_length/1609}') #meter to mile conversion

            #GPX Download
            file_mem = BytesIO()
            osmnx.utils_graph.graph_to_gdfs(sub)[0].reset_index()["geometry"].to_file(file_mem,'GPX')
            st.download_button(label='download',file_name="Route.gpx",mime="application/gpx+xml",data=file_mem)
    
        else:
            print('There was an error with the min cost flow problem')

if __name__ == "__main__":
    main()
