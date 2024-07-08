import streamlit as st
import requests
import pandas as pd
import json
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random


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
API_RATE_LIMIT = 200
DEBUG = False


def countdown(time_in_seconds=30):
    seconds = time_in_seconds
    while seconds >= 0:
        if DEBUG:
            print_color(f"Countdown... {seconds} seconds", bcolors.WARNING)
        time.sleep(1)
        seconds -= 1


global_req_count = 0
timestamp = st.empty()

current_month = datetime.now().month
current_year = datetime.now().year

months = [current_month + 3, current_month +
          2, current_month + 1, current_month]

if datetime.now().day >= 15:
    months.insert(0, current_month + 4)

months = [month if month <= 12 else month - 12 for month in months]

month = st.selectbox("Select Month", months)
inGroup = st.selectbox("Group or Inidividual", ("group", "individual"))
date_timelist_dict = {}
TIMESLOT_SET = None


def query_time_list(date_string):
    # get time list

    query_body = {
        'eventAk': 'LVR.EVN15',
        'eventName': 'performance.read.nt',
        'selectedDate': date_string,
        'eventCode': 'MusWeb'
    }
    if inGroup == "group":
        query_body = {
            **query_body,
            'eventCode': 'GA',
            'eventAk': 'LVR.EVN21'
        }

    r = requests.post(url=API_ENDPOINT, data=query_body)
    # extracting response text
    response_dict = json.loads(r.text)

    performance_list = response_dict['api']['result']['performanceList']
    time_list = [perf['perfTime'] for perf in performance_list]

    return time_list


def query_timeslot_availability(date, performanceId, performanceAk, retries=3):

    try:
        query_body = {
            'eventName': 'ticket.list',
            'dateFrom': date,
            'eventCode': 'GA' if inGroup == 'group' else 'MusWeb',
            'performanceId': performanceId,
            'priceTableId': '1',
            'performanceAk': performanceAk
        }
        if DEBUG:
            print(f'{date} {performanceId} {performanceAk}')

        r = requests.post(url=API_ENDPOINT, data=query_body)

        if DEBUG:
            if "Request unsuccessful." not in r.text and "GenericError" not in r.text:
                print_color("REQUEST SUCCESS.", bcolors.OKCYAN)
                # print_color(response_dict, bcolors.WARNING)
        # extracting response text
        response_dict = json.loads(r.text)

        # determine if individual or group
        product_list_index = 0 if inGroup == 'group' else 1
        product_list = response_dict['api']['result']['product.list']
        if len(product_list) > 2 and product_list[product_list_index]['available'] > 0:
            return True
        return False

    except Exception as e:
        print_color(f"{r.text}", bcolors.FAIL)


def query_data(month, containerlist):
    print("QUERY DATA CALLED")
    # data to be sent to api
    global TIMESLOT_SET
    global global_req_count
    data = {
        'year': current_year if month >= current_month else current_year + 1,
        'month': month,
        'eventCode': 'GA',
        'eventAk': 'LVR.EVN21',
        'eventName': 'date.list.nt',
    } if inGroup == "group" else {
        'year':  current_year if month >= current_month else current_year + 1,
        'month': month,
        'eventCode': 'GA',
        'eventAk': 'LVR.EVN15',
        'eventName': 'date.list.nt',
    }
    # sending post request and saving response as response object
    r = requests.post(url=API_ENDPOINT, data=data)

    # extracting response text
    response_dict = json.loads(r.text)

    date_list = response_dict['api']['result']['dateList']
    date_string_list = [date['date'] for date in date_list]
    if len(date_list) == 0:
        containerlist[0].text(
            f"Tickets for {month} has not yet been released!")

    # get timeslot of each date
    if TIMESLOT_SET != (month, inGroup):
        start_time = time.time()
        print_color("Getting timeslot ...", bcolors.OKCYAN)
        global_req_count += len(date_string_list)

        if global_req_count > API_RATE_LIMIT:
            print_color("Exceed limit. Sleep...", bcolors.WARNING)
            countdown(60)
            global_req_count = len(date_string_list)

        with st.spinner(text="fetching timeslot list"):
            with ThreadPoolExecutor(max_workers=10) as executor:
                def get_date_timeslots(date_string):
                    if DEBUG:
                        print(f"Getting date {date_string}")
                    date_timelist_dict[date_string] = query_time_list(
                        date_string)
                executor.map(get_date_timeslots, date_string_list)

            TIMESLOT_SET = (month, inGroup)
        end_time = time.time()

        print_color(
            f"Get timeslot taken: {end_time - start_time} seconds", bcolors.OKCYAN)

        print_color("backoff... 5 seconds", bcolors.WARNING)
        countdown(5)
    # get per date object
        # eventName
        # dateFrom
        # eventCode
        # performanceId
        # priceTableId
        # performanceAk
        # performanceId
        # to obtain per date object

    # louvre has an API limit of 250 requests per 60 seconds
    for index, dateObj in enumerate(date_list):
        global_req_count += len(dateObj['performanceRefList'])
        if global_req_count > API_RATE_LIMIT:
            print_color("Exceed limit. Sleep...", bcolors.WARNING)
            countdown(60)

            global_req_count = len(dateObj['performanceRefList'])

        with container_list[index].container() as placeholder:
            weekday = pd.Timestamp(dateObj['date'])
            available_timeslots = list()

            with ThreadPoolExecutor(max_workers=10) as executor:
                def check_availability(i, timeslot):
                    if query_timeslot_availability(date=dateObj['date'], performanceId=timeslot['id'], performanceAk=timeslot['ak']):
                        available_timeslots.append(
                            {"index": i, "timeslot": timeslot['available']})

                executor.map(lambda x: check_availability(
                    *x), enumerate(dateObj['performanceRefList']))

            print_color(
                f"{dateObj['date']} {weekday.day_name()}", bcolors.OKBLUE, end=" ")

            datestringAvail = f"**:blue[{dateObj['date']} {weekday.day_name()}]**"

            if len(available_timeslots):
                print_color('available', bcolors.OKGREEN)
                datestringAvail += " :green[available]"
            else:
                print_color('not available', bcolors.FAIL)
                datestringAvail += " :red[unavailable]"

            st.write(datestringAvail)

            available_timeslots = sorted(
                available_timeslots, key=lambda timeslot: timeslot['index'])

            t = ""
            for i, timeslot in enumerate(available_timeslots):
                index = timeslot['index']
                print(f"[{date_timelist_dict[dateObj['date']][index]}]",
                      end=" " if i % 4 else "\n")
                t += f"[{date_timelist_dict[dateObj['date']][index]}]"
            print("")
            st.write(t)


container_list = [st.empty() for _ in range(31)]

while 1:
    print_color("UPDATE!", bcolors.OKGREEN)
    timestamp.text(f"Updated at {datetime.now()}")
    query_data(month, container_list)
