# [generate_db.py]
#   Conversion from time-series data stored in git history
#   to sqlite db files

LIVE_DATA_ROOT = '../live-fhda-class-data/data/'

class Config:
    interval_time = 10
    full_reset = True

    def __init__(self, interval_time = 10, full_reset = True):
        self.interval_time = interval_time
        self.full_reset = full_reset

class Settings:
    start_sha = None
    end_sha = None
    snapshot_sha = None
    term_codes = None
    term_colors = None

    def __init__(self, term_codes, start_sha = None, end_sha = None, snapshot_sha = None, term_colors = ['cyan', 'yellow']):
        self.term_codes = term_codes
        self.term_colors = term_colors
        self.start_sha = start_sha
        self.end_sha = end_sha
        self.snapshot_sha = snapshot_sha

Summer2020 = Settings(
    term_codes={'fh': '202111', 'da': '202112'},
    start_sha=None,
    # The following commented SHA has lots of courses deleted
    # end_sha='5237c91feacf45068eb1aad3ee2a6c3dd2574815'
    end_sha='2f0fe2d87d60312e0d8f745486ac1642095a3322',
    snapshot_sha='030a30c4856c4c5a93aba77830a3b91a238ba5a8'
)

Fall2020 = Settings(
    term_codes={'fh': '202121', 'da': '202122'},
    start_sha='88860f841a62752789960b7c729749a28d896d3b',
    end_sha='caba60a62f595c825862d12423bac5b29af2fd5d'
)

Winter2021 = Settings(
    term_codes={'fh': '202131', 'da': '202132'},
    start_sha='06a4a8fdcfebba3bbe73d38993643770bc479f65',
    end_sha=None
)

TERM_CODES_TO_CONFIG = {
    term: config
    for config in [Summer2020, Fall2020, Winter2021]
    for term in config.term_codes.values()
}
