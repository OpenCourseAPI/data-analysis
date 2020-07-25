import os
import click

from generate_db import setup_cmd, Config, GitHistoryConverter, Summer2020, Fall2020

@click.group(context_settings=dict(max_content_width=120))
def cli():
    pass

setup_cmd(cli, 'generate')

@cli.command('start')
@click.pass_context
def start(ctx):
    'Start the data analysis web app (streamlit)'
    os.system('pipenv run streamlit run app.py')

@cli.command('to_csv')
@click.argument('src')
@click.argument('dest', required=False)
def to_csv(src, dest):
    'Convert an sqlite DB into a .csv file'
    dest = dest or src.replace('.sqlite3', '.csv').replace('.db', '.csv')
    os.system(f'sqlite3 -header -csv {src} "select * from classes;" > {dest}')

if __name__ == '__main__':
    cli() # pylint: disable=no-value-for-parameter

