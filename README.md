# Data Analysis
<sub>By Open Course API</sub>

## Prerequisites

- Python 3.7, `pip`, and `pipenv`
- Energy to start hacking 🚀

## Get Started

Install [`pipenv`](https://pypi.org/project/pipenv/) if you haven't already:

```bash
pip install pipenv
# OR
pip3 install pipenv
```

Clone [LiveMyPortalData](https://github.com/OpenCourseAPI/LiveMyPortalData.git) and this repo, and install its dependencies:

```bash
mkdir opencourse
cd opencourse

git clone https://github.com/OpenCourseAPI/LiveMyPortalData.git
git clone https://github.com/OpenCourseAPI/DataAnalysis.git

cd DataAnalysis
pipenv install # this may take some time
```

> Note: it is recommended to create a folder such as `opencourse` and clone these repos in that folder, for better organization and usability of the repos.

## Launch

Run the following in your terminal:

```bash
pipenv run cli start
```

You should see something like:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.XX:8501
```

Navigate to the specified URL in your browser and enjoy!

## Advanced

### Manually creating SQLite DBs

To manually generate `db/<term>.sqlite3` files, run the following:

```bash
pipenv run cli generate [--term Fall2020] [--interval-time 60] [OPTIONS]
```

For more information, use:

```bash
pipenv run cli generate --help
```

### Dump SQLite DB to CSV

To convert an SQLite DB file into CSV format, run the following:

```bash
pipenv run cli to_csv SRC_FILE [DEST_FILE]

# Examples:
pipenv run cli to_csv db/temp_202131.sqlite3 # will generate db/temp_202131.csv
pipenv run cli to_csv db/temp_202131.sqlite3 dump.csv # specify custom file
```

For more information, use:

```bash
pipenv run cli to_csv --help
```

## Contributing

We welcome all contributions! Have an idea or found a bug? Feel free to open an issue or a PR.

## License

The code in this repo is licensed under the [MIT license](LICENSE.md).
