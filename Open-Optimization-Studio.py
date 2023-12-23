import streamlit as st

def main():
    st.set_page_config(
        page_icon="🌐"
    )
    st.title("🌐 Open Optimization Studio")
    st.subheader("Web-Based Optimization Powered by Google OR-Tools")

    st.write(
        """
          Plan your next road trip (🚚 Trip Planning) and what to pack for it (🎒 Knapsack), figure out when to get your work done (⌚ Time Blocking),
          mix up your running routine (🏃 Running Routes) or learn more about formulating and solving your own optimizaton problems (💻 Linear Programming).
          
          Use the sidebar to navigate to the various modules. To learn more about how they work and examples of how to use them, check out the [User Guide](https://jbsooter.github.io/Open-Optimization-Studio/). 
          
          This work has been supported by an Honors College Research Grant. 
          
        """
    )

    st.write("\n")
    col1,col2,col3,col4 = st.columns([1,1,1,1])

    col1.link_button("Github", url="https://github.com/jbsooter/Open-Optimization-Studio")
    col2.link_button("User Guide",url="https://jbsooter.github.io/Open-Optimization-Studio/" )
    col3.link_button("Google OR-Tools", url="https://developers.google.com/optimization/")
    col4.link_button("Streamlit ", url="https://streamlit.io/")

    col1.link_button("Open Route Service", url="https://openrouteservice.org/")
    col2.link_button("Open Elevation", url="https://www.open-elevation.com/")
    col3.link_button("OSMnx",url="https://osmnx.readthedocs.io/en/stable/")

if __name__ == "__main__":
    main()