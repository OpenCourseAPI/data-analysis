"""
Converts time-series course data stored as a git repo into an sqlite database

"""

import sqlite3
import json
import math
import os
from os.path import join
from subprocess import PIPE, run
from datetime import datetime, timedelta

import numpy as np

from colors import Colors
from settings import Summer2020, Fall2020, Config

CONFIG = Config()

dates = []
shas = []


def print_info(m):
    print(f'{Colors.CGREEN}[INFO]{Colors.CEND} ' + m)


def nearest_ind(items, pivot):
    time_diff = np.abs([date - pivot for date in items])
    return time_diff.argmin(0)


def git(cmd):
    os.system(f'cd {CONFIG.data_root} && git {cmd} --quiet')


def run_read(cmd):
    result = run(cmd, stdout=PIPE, stderr=PIPE,
                 universal_newlines=True, shell=True)
    return result.stdout.strip()


def gitShow(q):
    return run_read(f'cd {CONFIG.data_root} && git show {q} --quiet')


def add_commit(x):
    x['date'] = datetime.fromtimestamp(int(x['date'].replace(" +0000", "")))
    dates.append(x['date'])
    shas.append(x['commit'])


# Convert this to a cross-platform script (probably rewrite in python)
LOG_COMMAND = """git log \
    --date=raw \
    --pretty=format:'{%n  "commit": "%H",%n  "author": "%aN <%aE>",%n  "date": "%ad",%n  "message": "%f"%n},' \
    $@ | \
    perl -pe 'BEGIN{print "["}; END{print "]\n"}' | \
    perl -pe 's/},]/}]/'
"""


def populate_changelog(settings):
    rawlog = run_read(f'cd {CONFIG.data_root}/.. && ' + LOG_COMMAND)
    snapshots = list(
        filter(lambda c: c['message'] == 'Update-data', json.loads(rawlog)))

    # TODO: make the following loops more efficient
    if settings.end_sha:
        for i, s in enumerate(snapshots):
            if s['commit'] == settings.end_sha:
                snapshots = snapshots[i:]
                break

    if settings.start_sha:
        for i, s in enumerate(snapshots):
            if s['commit'] == settings.start_sha:
                snapshots = snapshots[:i]
                break

    for s in snapshots:
        add_commit(s)


def floor_date(tm):
    # return tm - timedelta(minutes=tm.minute % 10,
    #                       seconds=tm.second,
    #                       microseconds=tm.microsecond)

    return tm - timedelta(minutes=tm.minute,
                          #   hours=tm.hour % 1,
                          seconds=tm.second,
                          microseconds=tm.microsecond)


class GitHistoryConverter:
    settings = None
    config = None

    abort = False
    cur_date = None
    cur_term = None
    term_index = None

    def __init__(self, settings, config):
        self.settings = settings
        self.config = config

    def convert(self):
        print_info('Starting up...')
        print_info('Use Ctrl+C to gracefully exit early')
        git('checkout master')
        git('pull')
        populate_changelog(self.settings)

        for i, (name, term) in enumerate(self.settings.term_codes.items()):
            self.cur_term = name.upper()
            self.term_index = i
            self.parse(name, term)

        print_info('That is it for now!')

    def parse(self, name, term):
        conn = sqlite3.connect(f'db/temp_{term}.sqlite3')
        c = conn.cursor()

        start_date = None

        if not CONFIG.full_reset:
            tableExists = c.execute(
                'SELECT name FROM sqlite_master WHERE type="table" AND name="classes"').fetchone()
            if tableExists and tableExists[0]:
                latest_item = c.execute(
                    'SELECT * FROM classes ORDER BY time DESC LIMIT 1').fetchone()
                if latest_item:
                    start_date = datetime.fromisoformat(latest_item[0])
                    print_info(
                        f'Skipping full reset. Starting from {start_date}')
            # continue

        else:
            c.execute('DROP TABLE IF EXISTS classes')
            c.execute("""CREATE TABLE classes (
                            time TIMESTAMP,
                            CRN INT,
                            status TEXT,
                            seats INT,
                            wait_seats INT,
                            wait_cap INT
                        )""")
            c.execute('CREATE UNIQUE INDEX time_crn ON classes (time, CRN)')

        cmds = []

        self.snapshot(c, term)
        conn.commit()

        try:
            self.loop(term, start_date, cmds)
        except KeyboardInterrupt:
            print(f'\r{self.add_term(term)} Exited early at',
                  self.cur_date, '             ', end='\r')
            self.abort = True
            pass
        finally:
            MSG_WRITING = 'Inserting rows into DB...'
            MSG_WROTE = 'Finished writing to DB   '

            print(f'\n{self.add_term(term)} ' + MSG_WRITING, end='\r')
            c.executemany('INSERT INTO classes VALUES(?, ?, ?, ?, ?, ?)', cmds)
            conn.commit()
            conn.close()
            print(f'{self.add_term(term)} {MSG_WROTE}')

    def snapshot(self, c, term):
        c.execute('DROP TABLE IF EXISTS snapshot')
        c.execute("""CREATE TABLE snapshot (
                        CRN INT,
                        dept TEXT,
                        section TEXT,
                        course TEXT,
                        description TEXT,
                        campus TEXT,
                        units FLOAT,
                        start DATE,
                        end DATE,
                        status TEXT,
                        seats INT,
                        wait_seats INT,
                        wait_cap INT
                    )""")
        c.execute('CREATE UNIQUE INDEX crn ON snapshot (CRN)')

        sha = self.settings.snapshot_sha
        cmds = []
        self.git_magic2(term, cmds, sha)
        c.executemany(
            'INSERT INTO classes VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', data)

    def loop(self, term, start, cmds):
        dlatest = floor_date(dates[0])
        dfirst = start or floor_date(dates[-1])

        delta = (dlatest - dfirst).total_seconds() / 60
        iter_count = math.ceil(delta / CONFIG.interval_time)

        print(f'{self.add_term(term)} Analyzing term {term} from {dfirst} to {dlatest}\n     Chunks: {iter_count}')

        self.cur_date = dfirst

        for i in range(iter_count):
            if self.abort:
                break

            di = nearest_ind(dates, self.cur_date)

            print(f'{self.add_term(term)} Analyzing Commit: i =',
                  di, shas[di][0:6], end='\r')

            self.git_magic(term, cmds, shas[di], self.cur_date)
            self.cur_date += timedelta(minutes=CONFIG.interval_time)

    def git_magic2(self, term, cmds, sha):
        db = json.loads(gitShow(f'{sha}:data/{term}_database.json'))

        for dept in db:
            table = db[dept]['1']

            for courses in table.values():
                for ccc in courses.values():
                    cl = ccc[0]

                    print(cl)

                    data = [
                        cl['CRN'],
                        cl['dept'],
                        cl['section'],
                        cl['course'],
                        cl['desc'],
                        cl['campus'],
                        cl['units'],
                        cl['start'],
                        cl['end'],
                        cl['status'],
                        cl['seats'],
                        cl['wait_seats'],
                        cl['wait_cap'],
                    ]
                    cmds.append(data)

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

    def add_term(self, t):
        return f'{self.settings.term_colors[self.term_index]}[{self.cur_term}]{Colors.CEND}'


if __name__ == '__main__':
    converter = GitHistoryConverter(Summer2020, CONFIG)
    converter.convert()
