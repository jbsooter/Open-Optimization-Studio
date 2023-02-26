#!/bin/bash
#use on mac
#set wd to software directory
cd "$(dirname "$0")"

#create venv
python3 -m venv ./venv

#activate venv
source venv/bin/activate

#install requirements
python3 -m pip install -r ./requirements.txt

#launch app
streamlit run ./Open-Optimization-Studio.py
