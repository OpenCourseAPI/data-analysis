# Data Analysis
<sub>By Open Course API</sub>

## Prerequisites

- Python 3.7, `pip`, and `pipenv`
- A happy mood

## Get Started

Install `pipenv` if you haven't already:

```bash
pip install pipenv
# OR
pip3 install pipenv
```

Clone this repo and install its dependencies:

```bash
mkdir opencourse
cd opencourse

git clone https://github.com/OpenCourseAPI/DataAnalysis.git
cd DataAnalysis

pipenv install # this will take time
```

> Note: it is recommended to create a folder such as `opencourse` and clone these repos in that folder for better organization and usability.

## Launch

Run the following:

```bash
pipenv run streamlit run app.py
```

You should see something like:

```sh
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.10:8501
```

Navigate to the URL specified in your browser and enjoy!
