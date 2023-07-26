import streamlit as st
import requests
import pandas as pd
import json
import requests
import time
from datetime import datetime


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_color(string, color, end='\n'):
    print(f"{color}{string}{bcolors.ENDC}", end=end)

# defining the api-endpoint
API_ENDPOINT = "https://www.ticketlouvre.fr/louvre/b2c/RemotingService.cfc?method=doJson"

timestamp = st.empty()

month = st.selectbox("Select Month",(10, 9, 8))
inGroup = st.selectbox("Group or Inidividual", ("group", "individual"))
date_timelist_dict = {}
TIMESLOT_SET = False


def query_time_list(date_string):
    # get time list

    query_body = {
        'eventAk': 'LVR.EVN15',
        'eventName': 'performance.read.nt',
        'selectedDate': date_string
    }
    r = requests.post(url = API_ENDPOINT, data = query_body)
    # extracting response text
    response_dict = json.loads(r.text)

    performance_list = response_dict['api']['result']['performanceList']
    time_list = [ perf['perfTime'] for perf in performance_list ]

    return time_list

def query_data(month, containerlist):
    # data to be sent to api
    global TIMESLOT_SET
    data = {
        'year': 2023,
        'month': month,
        'eventCode': 'GA',
        'eventAk':'LVR.EVN21',
        'eventName': 'date.list.nt',
        'productId': 2399
        } if inGroup == "group" else {
        'year': 2023,
        'month': month,
        'eventCode': 'GA',
        'eventAk':'LVR.EVN15',
        'eventName': 'date.list.nt',
        }

    # sending post request and saving response as response object
    r = requests.post(url = API_ENDPOINT, data = data)

    # extracting response text
    response_dict = json.loads(r.text)

    date_list = response_dict['api']['result']['dateList']
    date_string_list = [date['date'] for date in date_list]

    # get timeslot of each date
    if not TIMESLOT_SET:
        with st.spinner(text="fetching timeslot list"):
            for date_string in date_string_list:
                date_timelist_dict[date_string] = query_time_list(date_string)
            TIMESLOT_SET = True

    for index, dateObj in enumerate(date_list):
        with container_list[index].container() as placeholder:
            weekday = pd.Timestamp(dateObj['date'])
            available_timeslots = list()

            for i, timeslot in enumerate(dateObj['performanceRefList']):
                if timeslot['available'] > 0:
                        available_timeslots.append({"index": i, "timeslot": timeslot['available']})

            print_color(f"{dateObj['date']} {weekday.day_name()}", bcolors.OKBLUE, end=" ")

            datestringAvail = f"**:blue[{dateObj['date']} {weekday.day_name()}]**"

            if len(available_timeslots):
                print_color('available', bcolors.OKGREEN)
                datestringAvail += " :green[available]"
            else:
                print_color('not available', bcolors.FAIL)
                datestringAvail += " :red[unavailable]"

            st.write(datestringAvail)

            t = ""
            for i, timeslot in enumerate(available_timeslots):
                index = timeslot['index']
                print(f"[{date_timelist_dict[dateObj['date']][index]}]", end= " " if i % 4 else "\n")
                t += f"[{date_timelist_dict[dateObj['date']][index]}]"
            print("")
            st.write(t)

container_list = [ st.empty() for _ in range(31) ]

while 1:
    timestamp.text(f"Updated at {datetime.now()}")
    query_data(month, container_list)
    time.sleep(1)