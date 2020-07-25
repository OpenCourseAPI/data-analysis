'''
Converts time-series course data stored in git commit history into an SQLite database

Usage: `pipenv run cli generate [--term Fall2020] [OPTIONS]`
More Info: `pipenv run cli generate --help`

Direct Usage [not recommended]: `pipenv run generate_db.py [OPTIONS]`
'''

import sqlite3
import json
import math
import os
from os.path import join
from subprocess import PIPE, run
from datetime import datetime, timedelta

import numpy as np
import click

from settings import LIVE_DATA_ROOT, Summer2020, Fall2020, Config

'''
Logging utilities
'''

# Print message to console prefixed with `info`
def print_info(m):
    click.echo(click.style('info', fg='green') + ' ' + m)

# Print message to console prefixed with `warn`
def print_warning(m):
    click.echo(click.style('warn', fg='yellow') + ' ' + m)

# Print message to console prefixed with `err`
def print_error(m):
    click.echo(click.style('err ', fg='red') + ' ' + m)

'''
Date utilities
'''

# Find and return the index of the nearest date in a list of items
def nearest_date(items, pivot):
    time_diff = np.abs([date - pivot for date in items])
    return time_diff.argmin(0)

# Round a date
def floor_date(tm):
    return tm - timedelta(minutes=tm.minute % 10,
                          seconds=tm.second,
                          microseconds=tm.microsecond)

    # return tm - timedelta(minutes=tm.minute,
    #                       #   hours=tm.hour % 1,
    #                       seconds=tm.second,
    #                       microseconds=tm.microsecond)

'''
Git / Shell utilities
'''

# Run a shell command and return its output
def run_read(cmd):
    result = run(cmd, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True, shell=True)
    return result.stdout.strip()

# Run a git command
def git(cmd):
    os.system(f'cd {LIVE_DATA_ROOT} && git {cmd} --quiet')

# Run and return output of `git show` (for viewing file at commit)
# Ex. `git show {sha}:data/{term}_database.json`
def gitShow(query):
    return run_read(f'cd {LIVE_DATA_ROOT} && git show {query} --quiet')

'''
Git changelog generator
'''

# TODO: Convert this to a cross-platform script (probably rewrite in python)
LOG_COMMAND = '''git log \
    --date=raw \
    --pretty=format:'{%n  "sha": "%H",%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f"%n},' \
    $@ | \
    perl -pe 'BEGIN{print "["}; END{print "]\n"}' | \
    perl -pe 's/},]/}]/'
'''

def populate_changelog(settings):
    rawlog = run_read(f'cd {LIVE_DATA_ROOT}/.. && ' + LOG_COMMAND)
    snapshots = list(
        filter(lambda c: c['message'] == 'Update-data', json.loads(rawlog)))

    # TODO: make the following loops more efficient
    if settings.end_sha:
        for i, s in enumerate(snapshots):
            if s['sha'] == settings.end_sha:
                snapshots = snapshots[i:]
                break

    if settings.start_sha:
        for i, s in enumerate(snapshots):
            if s['sha'] == settings.start_sha:
                snapshots = snapshots[:i]
                break

    return snapshots

'''
Converts cool stuff into another format
'''
class GitHistoryConverter:
    # External config
    settings = None
    config = None

    # Hooks
    setup_progress = None
    update_progress = None

    dates = []
    shas = []

    abort = False
    cur_date = None
    cur_term = None
    term_index = None

    def __init__(self, settings, config, setup_progress=None, update_progress=None):
        self.settings = settings
        self.config = config
        self.setup_progress = setup_progress
        self.update_progress = update_progress

    def convert(self):
        print_info('Starting up data converter...')
        print_info('Use Ctrl+C to gracefully exit early')
        git('checkout master')
        git('pull')

        commits = populate_changelog(self.settings)
        for commit in commits:
            timestamp = int(commit['date'].replace(' +0000', ''))
            self.dates.append(datetime.fromtimestamp(timestamp))
            self.shas.append(commit['sha'])

        for i, (name, term) in enumerate(self.settings.term_codes.items()):
            # Currently, abort acts like "skip ahead"
            self.abort = False
            self.cur_date = None
            self.cur_term = name.upper()
            self.term_index = i
            self.parse_term(term)

        print_info('That is it for now!')

    def setup_db(self, term: str):
        conn = sqlite3.connect(f'db/temp_{term}.sqlite3')
        c = conn.cursor()
        alreadyExists = False

        if not self.config.full_reset:
            tableExists = c.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="classes"').fetchone()

            if tableExists and tableExists[0]:
                alreadyExists = True

        if not alreadyExists:
            c.execute('DROP TABLE IF EXISTS classes')
            c.execute('''CREATE TABLE classes (
                            time TIMESTAMP,
                            CRN INT,
                            status TEXT,
                            seats INT,
                            wait_seats INT,
                            wait_cap INT
                        )''')
            c.execute('CREATE UNIQUE INDEX time_crn ON classes (time, CRN)')

        if self.setup_meta_table(c):
            meta = self.read_meta(c)
        else:
            meta = None

        return (conn, c, alreadyExists, meta)

    def setup_meta_table(self, c: sqlite3.Cursor):
        alreadyExists = False
        tableExists = c.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="meta"').fetchone()

        if tableExists and tableExists[0]:
            alreadyExists = True

        if not alreadyExists:
            c.execute('DROP TABLE IF EXISTS meta')
            c.execute('''CREATE TABLE meta (
                            key TEXT UNIQUE,
                            value TEXT
                        )''')

        return alreadyExists

    def write_meta(self, c: sqlite3.Cursor):
        c.execute('INSERT OR REPLACE INTO meta VALUES(?, ?)', ['interval', self.config.interval_time])

    def read_meta(self, c: sqlite3.Cursor):
        rows = c.execute('SELECT * FROM meta').fetchall()
        metadata = {row[0]:row[1] for row in rows}
        return metadata

    def parse_term(self, term):
        (conn, c, tableExists, meta) = self.setup_db(term)

        start_date = None

        if not self.config.full_reset and tableExists:
            latest_item = c.execute('SELECT * FROM classes ORDER BY time DESC LIMIT 1').fetchone()

            if latest_item:
                start_date = datetime.fromisoformat(latest_item[0])
                print_info(f'Skipping full reset')
                click.echo(f'     {click.style("Start Date:", dim=True)} {start_date}')

            if meta and (int(meta['interval']) != self.config.interval_time):
                print_warning(f'Ignoring specified interval time ({self.config.interval_time} min)')
                print_warning(f'Using the existing time instead ({meta["interval"]} min)')
                self.config.interval_time = int(meta['interval'])

        cmds = []

        try:
            self.loop(term, start_date, cmds)
        except KeyboardInterrupt:
            print(f'\r{self.fterm()} Exited early at', self.cur_date, '             ', end='\r\n')
            self.abort = True
        finally:
            MSG_WRITING = 'Inserting rows into DB...'
            MSG_WROTE = 'Finished writing to DB   '

            print(f'{self.fterm()} ' + MSG_WRITING, end='\r')
            # try:
            c.executemany('INSERT INTO classes VALUES(?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING', cmds)
            # except sqlite3.IntegrityError:
                # click.echo('uh oh', err=True)
                # pass
            self.write_meta(c)

            conn.commit()
            conn.close()
            print(f'{self.fterm()} {MSG_WROTE}')

    def loop(self, term, start, cmds):
        dlatest = floor_date(self.dates[0])
        dfirst = start or floor_date(self.dates[-1])

        interval = self.config.interval_time
        delta = (dlatest - dfirst).total_seconds() / 60
        iter_count = math.ceil(delta / interval)

        click.echo(f'{self.fterm()} Analyzing term {click.style(term, bold=True)}')
        click.echo(f'     {click.style("Start:", dim=True)} {dfirst}')
        click.echo(f'     {click.style("End:  ", dim=True)} {dlatest}')
        click.echo(f'     {click.style("Data: ", dim=True)} {iter_count} chunks {click.style("of", dim=True)} {interval} min')

        self.cur_date = dfirst

        if self.setup_progress:
            self.setup_progress(self.cur_term)

        with click.progressbar(
            range(iter_count),
            fill_char='█',
            bar_template="     [%(bar)s]  %(info)s"
        ) as bar:
            for i in bar:
                if self.abort:
                    break

                nearest_date_index = nearest_date(self.dates, self.cur_date)

                # Disable progress bar and enable the following for advanced debugging
                # print(f'{self.fterm()} Analyzing Commit: i =',
                #     nearest_date_index, self.shas[nearest_date_index][0:6], end='\r')

                self.git_magic(term, cmds, self.shas[nearest_date_index], self.cur_date)
                self.cur_date += timedelta(minutes=interval)

                if self.update_progress:
                    self.update_progress((i + 1) / iter_count)

    def git_magic(self, term, cmds, sha, date):
        db = json.loads(gitShow(f'{sha}:data/{term}_database.json'))

        for dept in db:
            table = db[dept]['1']

            for courses in table.values():
                for ccc in courses.values():
                    cl = ccc[0]

                    data = [
                        date,
                        cl['CRN'],
                        cl['status'],
                        cl['seats'],
                        cl['wait_seats'],
                        cl['wait_cap'],
                    ]
                    cmds.append(data)

    def fterm(self):
        name = self.cur_term.ljust(4)
        color = self.settings.term_colors[self.term_index]
        return click.style(name, fg=color)

TERM_NAMES_TO_CONFIG = {
    'summer2020': Summer2020,
    'fall2020': Fall2020,
}
DEFAULT_TERM = 'fall2020'

def setup_cmd(ctx, name=None):
    choices = click.Choice(choices=TERM_NAMES_TO_CONFIG.keys(), case_sensitive=False)

    @ctx.command(name)
    @click.option('--term', '-t', type=choices, default=DEFAULT_TERM,
                  metavar='<quarter><year>', help='The term to generate data for, such as "Fall2020"')
    @click.option('--interval-time', '-i', type=click.IntRange(1, 60), default=60,
                  metavar='<minutes>', help='The interval to generate time-series data')
    @click.option('--skip-reset', is_flag=True, default=False,
                  help='Only add new data to existing DBs')
    def convert(term: str, interval_time: int, skip_reset: bool):
        """Convert Git history repos into Sqlite3 database."""
        config = Config(interval_time, not skip_reset)
        converter = GitHistoryConverter(TERM_NAMES_TO_CONFIG[term.lower()], config)
        converter.convert()

    return convert

if __name__ == '__main__':
    cmd = setup_cmd(click)
    cmd() # pylint: disable=no-value-for-parameter
