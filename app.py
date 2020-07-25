# pylint: disable=E1120
# See: https://github.com/streamlit/streamlit/issues/1536
# See: https://discuss.streamlit.io/t/error-no-value-for-argument-body-in-method-call-vs-code/1851/6

import os
import time
import json
import sqlite3
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests

from generate_db import GitHistoryConverter
from settings import Config, Summer2020, Fall2020

#
# Data and term configuration
#

ROOT = './'
TERM_CODES = {
    'Foothill: Summer 2020': '202111',
    'De Anza: Summer 2020' : '202112',
    'Foothill: Fall 2020'  : '202121',
    'De Anza: Fall 2020'   : '202122',
}
TERM_CODES_TO_CONFIG = {
    '202111': Summer2020,
    '202112': Summer2020,
    '202121': Fall2020,
    '202122': Fall2020,
}

# Workaround for a timezone bug in streamlit
# ORIGINAL_TIMEZONE = time.tzname[time.daylight]
# # os.environ['ORIG_TZ'] = time.tzname[time.daylight]
# try:
#     ORIGINAL_TIMEZONE = time.tzname[1]
#     # os.environ['ORIG_TZ']
# except IndexError:
#     ORIGINAL_TIMEZONE = time.tzname[0]

# print(ORIGINAL_TIMEZONE)

# https://github.com/streamlit/streamlit/issues/1061#issuecomment-642057212
os.environ['TZ'] = 'UTC'

#
# Data generator
#

progress_bar = None

def setup_progress_bar(name):
    global progress_bar

    st.sidebar.text(name)
    progress_bar = st.sidebar.progress(0)

def update_progress_bar(value):
    progress_bar.progress(value)

def generate_data(settings, interval, full_reset):
    st.sidebar.markdown('### Generating Data')
    del os.environ['TZ']
    # os.environ['TZ'] = ORIGINAL_TIMEZONE
    GitHistoryConverter(
        settings,
        Config(interval, full_reset),
        update_progress=update_progress_bar,
        setup_progress=setup_progress_bar
    ).convert()
    os.environ['TZ'] = 'UTC'
    st.caching.clear_cache()
    st.balloons()

#
# Database Utilities
#

@st.cache(allow_output_mutation=True)
def connect_db(term):
    # TODO: check thread safety
    conn = sqlite3.connect(f'{ROOT}db/temp_{term}.sqlite3', check_same_thread=False)
    c = conn.cursor()
    return c

@st.cache(hash_funcs={sqlite3.Cursor:id})
def data_exists(c):
    tableExists = c.execute(
        'SELECT name FROM sqlite_master WHERE type="table" AND name="classes"'
    ).fetchone()
    if tableExists and tableExists[0]:
        return True
    return False

#
# Queries
#

@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Cursor:id})
def get_all_classes(c):
    return c.execute('''
        SELECT
            time,
            SUM(seats),
            SUM(wait_seats),
            COUNT(case status when "Open" then 1 else null end) as open_classes,
            COUNT(case status when "Waitlist" then 1 else null end) as waitlist_classes,
            COUNT(case status when "Full" then 1 else null end) as full_classes
        FROM classes
        GROUP BY time;
    ''').fetchall()

@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Cursor:id})
def get_total_classes(c):
    return c.execute('''
        SELECT
            time,
            COUNT(CRN)
        FROM classes
        GROUP BY time;
    ''').fetchall()

@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Cursor:id})
def count_times(c):
    return c.execute('SELECT COUNT(time) FROM classes;').fetchone()

@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Cursor:id})
def get_available_crn(c):
    return c.execute('SELECT DISTINCT CRN FROM classes;').fetchall()

# TODO: hash
def get_one_class(c, dept, course):
    return c.execute('SELECT * FROM classes WHERE dept = ? and section = ?', [dept, course]).fetchall()

# TODO: hash
def get_one_class_by_crn(c, crn):
    return c.execute('SELECT * FROM classes WHERE CRN = ?', [crn]).fetchall()

#
# Utilities
#

# Create a date from an SQLite datetime string
def dt(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')

#
# Streamlit App
#

# Sidebar page navigation
st.sidebar.markdown('## NAVIGATION')
page = st.sidebar.radio('Select a page:', ['Home', 'API', 'Quickstart', 'About'])

# Home page, with all its graphs
if page == 'Home':
    '''
    # Data Analysis
    ### By [Open Course API](https://github.com/OpenCourseAPI/)
    ####
    Tip: Use the sidebar to change the term and control other settings.
    '''

    # Sidebar settings
    st.sidebar.markdown('## SETTINGS')
    term = st.sidebar.selectbox(
        'Choose a term: ', list(TERM_CODES.keys())
    )
    show_debug_info = st.sidebar.checkbox('Show debug information')
    show_advanced_options = st.sidebar.checkbox('Show advanced options')

    # Data generation options
    st.sidebar.markdown('## DATA')

    interval = 60
    if show_advanced_options:
        interval = st.sidebar.slider('Interval time (in minutes)', value=60, min_value=5, max_value=60, step=5)

    if st.sidebar.button('Update'):
        generate_data(Fall2020, interval, False)

    if st.sidebar.button('Regenerate'):
        generate_data(Fall2020, interval, True)

    # Main Page Content

    # Load database
    c = connect_db(TERM_CODES[term])

    # Generate data if necessary
    if not data_exists(c):
        generate_data(TERM_CODES_TO_CONFIG[TERM_CODES[term]], interval, True)

    # Get all class data aggregated by time
    class_data = get_all_classes(c)
    times = [dt(x[0]) for x in class_data]
    # total_times = countTimes(c)[0]

    if show_debug_info:
        l = len(class_data)
        start_date = l and class_data[0][0]
        end_index = (l - 1) or 0
        end_date = l and class_data[end_index][0]

        f'''
        ### Debug Info

        ```
        Term  - {term}
        Start - {dt(start_date).strftime('%b %d, %Y %I:%M %p')}
        End   - {dt(end_date).strftime('%b %d, %Y %I:%M %p')}
        ```
        '''

    '''
    ## All Classes
    ### Raw Data
    '''

    df = pd.DataFrame(
        [x[1:] for x in class_data],
        index=times,
        columns=['Seats', 'Wait Seats', 'Open Classes', 'Waitlist', 'Full']
    )
    df

    '''
    ### Open Seats By Time
    '''

    df = pd.DataFrame(
        [x[1:3] for x in class_data],
        index=times,
        columns=['Seats', 'Wait Seats']
    )
    st.line_chart(df)

    df2 = pd.DataFrame(
        [x[1:3] for x in class_data],
        index=pd.DatetimeIndex(times),
        columns=['Seats', 'Wait Seats']
    # )
    ).resample('D').mean()
    df = pd.DataFrame(
        [x[1:3] for x in class_data],
        index=pd.DatetimeIndex(times),
        columns=['Seats', 'Wait Seats']
    # ).shift()
    ).resample('D').mean().shift()
    st.line_chart(df.subtract(df2))

    '''
    ### Class Status By Time
    '''

    df = pd.DataFrame(
        [x[3:6] for x in class_data],
        index=times,
        columns=['Open', 'Waitlist', 'Full']
    )
    st.area_chart(df)

    '''
    ### Total Class Count By Time
    '''

    total_classes = get_total_classes(c)
    df = pd.DataFrame(
        [x[1:] for x in total_classes],
        index=[dt(x[0]) for x in total_classes],
        columns=['Classes']
    )
    st.line_chart(df)

    '''
    ### View Course History
    '''

    # dept = st.text_input('Department', 'CS')
    # course = st.text_input('Course / Section', '1A')
    crn = st.text_input('Enter a CRN', 10152)

    # crs = get_one_class(c, dept, course)
    crs = get_one_class_by_crn(c, crn)

    if crs and len(crs) > 0:
        df = pd.DataFrame(
            [x[3:5] for x in crs],
            index=[dt(x[0]) for x in crs],
            columns=['Seats', 'Wait Seats']
        )
        st.line_chart(df)

    else:
        'CRN not found! Available CRN:'
        # ', '.join([str(x[0]) for x in get_available_crn(c)])
        df = pd.DataFrame(get_available_crn(c))
        df

    '''
    ### That's it for now!

    Try changing the term above, or check back again later!

    Or, head over to [opencourse.dev](https://opencourse.dev).
    '''


# Owl API (playground, etc.)
if page == 'API':
    '''
    # Owl API
    ### More at [opencourse.dev](https://opencourse.dev)

    ## Playground
    '''

    PREFIX = 'https://opencourse.dev'
    endpoint = st.text_input('Enter an API url:', value='/fh/single?dept=CS&course=1A')

    response = requests.get(PREFIX + endpoint)
    response.raise_for_status()

    try:
        json = response.json()
        st.json(response.json())
    except:
        st.text(response.text)

    df = pd.DataFrame(sum(list(dict(json).values()), []))
    df


# Quickstart page (guides for buliding your own analysis)
if page == 'Quickstart':
    '''
    # Quickstart
    ## Build Your Own

    Interested in building your own analysis? We are too!
    Get started by opening `app.py` in a code editor, and try adding some stuff.
    For example:
    '''

    with st.echo():
        # Title and text
        st.subheader('Me vs. Others')
        st.write('This is a random but cool graph about me! What do you think?')

        # Line chart
        df = pd.DataFrame(
            [(i, pow(1.5, i)) for i in range(11)],
            columns=['People', 'Me']
        )
        st.line_chart(df)


# About page
if page == 'About':
    text = '''
    <style>
        .footer {
            color: #999;
        }
        .footer a {
            color: #4e8dc7 !important;
        }
    </style>

    # Open Course API

    <img src="https://avatars0.githubusercontent.com/u/40309595?s=200&v=4" width="80px" />

    ####

    Website: https://opencourse.dev/

    GitHub: https://github.com/OpenCourseAPI/

    ####

    <span class="footer">Made with ❤️ by [Madhav Varshney](https://github.com/madhavarshney)</span>
    '''
    st.markdown(text, unsafe_allow_html=True)
    ### [![GitHub Logo](https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png)](https://github.com/OpenCourseAPI/)
    ####
