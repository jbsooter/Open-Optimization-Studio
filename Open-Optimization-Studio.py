import streamlit as st

def main():
    st.set_page_config(
        page_icon="🌐"
    )
    st.title("🌐 Open Optimization Studio")
    st.subheader("Web-Based Optimization Powered by Google OR-Tools")

    st.write(
        """
          Plan your next road trip (🚚 Vehicle Routing), figure out when to get your work done (⌚ Time Blocking),
          mix up your running routine (🏃 Running Routes) or learn more about formulating and solving your own optimizaton problems (💻 Linear Programming).
          
          To learn more, check out the [User Guide](https://jbsooter.github.io/Open-Optimization-Studio/). 
          
        """
    )

if __name__ == "__main__":
    main()