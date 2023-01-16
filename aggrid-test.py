import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder

def load_obj_grid(df):
    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_column("obj", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["min","max"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True,height=65)

def load_constraints_grid(df):

    #builds a gridOptions dictionary using a GridOptionsBuilder instance.
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_column("inequality", editable=True, cellEditor='agSelectCellEditor',cellEditorParams={'values':["<=",">=","=","<",">"]})
    go = builder.build()

    #uses the gridOptions dictionary to configure AgGrid behavior and loads AgGrid
    AgGrid(df, gridOptions=go,editable=True,fit_columns_on_grid_load=True)

def add_row():
    #get existing
    old_df = st.session_state['df_mip']

    #create dataframe representing new row
    new_row = pd.DataFrame()
    for col in old_df.columns:
        new_row[col] = [0]

    #create and save new, combined dataframe
    st.session_state['df_mip'] = pd.concat([old_df, new_row])

def add_column():
    #get old data
    old_df = st.session_state['df_mip']

    #row and column lengths
    nrows = len(old_df)
    ncols = len(old_df.columns)

    #create new row with auto variable name
    st.session_state['df_mip'].insert(ncols-2,f"var{ncols}",[0]*nrows)
    st.session_state['df_obj'][f"var{ncols}"] = [0]

def main():
    #initialize session default data
    if 'df_mip' not in st.session_state:
        st.session_state['df_mip'] = pd.DataFrame({'var1': [1, 2, 3], 'var2': [4, 5, 6],'inequality':[">=","<=","=="],'RHS':[7,8,9]})
    if 'df_obj' not in st.session_state:
        st.session_state['df_obj'] = pd.DataFrame({'var1': [1], 'var2': [4],"obj":"max"})

    col1,col2 = st.columns([6,1])
    with col1:
        #load obj grid
        load_obj_grid(st.session_state.df_obj)
        #load input grid
        load_constraints_grid(st.session_state.df_mip)
        #allow for additional constraints
        st.button(label="\+ Constraint",on_click=add_row)
    with col2:
        #allow for additional variables
        st.button(label="\+ Variable",on_click=add_column)

    st.button(label="Solve")

if __name__ == "__main__":
    main()




