import json
import sqlite3
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt
# import tinydb

ROOT = "../livescripts/"
TERM_CODES = {
    'Foothill: Summer 2020': '202111',
    'De Anza: Summer 2020': '202112',
    'Foothill: Fall 2020': '202121',
    'De Anza: Fall 2020': '202122',
}

@st.cache(allow_output_mutation=True)
def connectDB(term):
    # TODO: check safety of multi-thread
    conn = sqlite3.connect(f'{ROOT}db/temp_{term}.sqlite3', check_same_thread=False)
    c = conn.cursor()
    return c

@st.cache(allow_output_mutation=True, hash_funcs={sqlite3.Cursor:id})
def getAllClasses(c):
    return c.execute("""
        SELECT
            time,
            SUM(seats),
            SUM(wait_seats),
            COUNT(case status when "Open" then 1 else null end) as open,
            COUNT(case status when "Waitlist" then 1 else null end) as wait,
            COUNT(case status when "Full" then 1 else null end) as full
        FROM classes
        GROUP BY time;
    """).fetchall()

def getOneClass(c, dept, course):
    return c.execute('SELECT * FROM classes WHERE dept = ? and section = ?', [dept, course]).fetchall()

def getOneClassByCrn(c, crn):
    return c.execute('SELECT * FROM classes WHERE CRN = ?', [crn]).fetchall()

def dt(dstr):
    return datetime.strptime(dstr, '%Y-%m-%d %H:%M:%S')

st.title('Data Analysis')
st.markdown('### By [Open Course API](https://github.com/OpenCourseAPI/)')

term = st.selectbox('Choose a term: ', list(TERM_CODES.keys()))

c = connectDB(TERM_CODES[term])
class_data = getAllClasses(c)

st.header('All Classes')
st.subheader('Raw Data')

df = pd.DataFrame(
    [x[1:] for x in class_data],
    index=[dt(x[0]) for x in class_data],
    columns = ['Seats', 'Wait Seats', 'Open Classes', 'Waitlist', 'Full']
)
df

st.subheader('Open Seats By Time')
df = pd.DataFrame(
    [x[1:3] for x in class_data],
    index=[dt(x[0]) for x in class_data],
    columns = ['Seats', 'Wait Seats']
)
st.line_chart(df)

st.subheader('Class Status By Time')
df = pd.DataFrame(
    [x[3:6] for x in class_data],
    index=[dt(x[0]) for x in class_data],
    columns = ['Open', 'Waitlist', 'Full']
)
st.area_chart(df)

st.subheader('View Course History')
# dept = st.text_input('Department', 'CS')
# course = st.text_input('Course / Section', '1A')
crn = st.text_input('CRN', 10152)

# crs = getOneClass(c, dept, course)
crs = getOneClassByCrn(c, crn)
df = pd.DataFrame(
    [x[3:5] for x in crs],
    index=[dt(x[0]) for x in crs],
    columns = ['Seats', 'Wait Seats']
)
st.line_chart(df)

st.markdown("""
### That's it for now!

Try changing the term above, or check back again later!

Or, head over to [opencourse.dev](https://opencourse.dev).""")
