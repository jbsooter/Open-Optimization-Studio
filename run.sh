#!/bin/bash
#set wd to software directory
cd "$(dirname "$0")"
#activate venv
source venv/bin/activate

#launch app
streamlit run ./Open-Optimization-Studio.py