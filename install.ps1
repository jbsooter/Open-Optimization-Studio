#use on windows
#Create Venv
py -m venv venv

#Activate venv
.\venv\Scripts\activate.ps1


#install packages
py -m pip install -r requirements.txt

#run app
streamlit run Open-Optimization-Studio.py