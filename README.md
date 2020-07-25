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
  Network URL: http://192.168.1.10:8501
```

Navigate to the URL specified in your browser and enjoy!

## Advanced

### Manually creating SQLite DBs

To manually generate `db/<term>.sqlite3` files, run the following:

```bash
pipenv run cli generate [--term Fall2020] [OPTIONS]
```

For more information, use:

```bash
pipenv run cli generate --help
```

## Contributing

We welcome all contributions! Have an idea or found a bug? Open an issue or PR!

_More info will follow, but in the meantime, get started by running the app as described above._

## License

The code in this repo is licensed under the MIT license.
