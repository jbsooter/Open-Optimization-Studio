#use on mac
#create venv
python3 -m venv venv

#activate venv
source env/bin/activate

#install requirements
python3 -m pip install -r requirements.txt

#launch app
streamlit run Open-Optimization-Studio.py