from .logdraft import LogDraft
import draftlog
import time
import sys
import ansi
import threading

# Imports the correct module according to
# Python version.
if sys.version_info[0] <= 2:
    import Queue as queue
else:
    import queue

"""
A background process to coordinate all the intervals
with their correct times rather than having clashing
multiple threads.
"""
class DaemonDrafter(threading.Thread):
    def __init__(self):
        super(DaemonDrafter, self).__init__()

        self.lcs = sys.stdout
        self.intervals = []
        self.counter = -1
        self.time_interval = 0

    # Returns a "LogDraft" object on the correct line
    def log(self, text="\n"):
        logdraft = LogDraft(self)
        self.lcs.write(text)
        return logdraft

    """
    What actually adds the interval.
    "Loader" specifies if the interval should
    affect when the draft actually exits.
    "Update" defines whether to overwrite the LogDraft
    line, or to add a new line afterwards.
    """
    def add_interval(self, logdraft, func, seconds, loader=False, update=True):
        if loader != None:
            loader = not loader

        self.intervals.append({
            "function":  func,
            "logdraft":  logdraft,
            "time"    :  seconds,
            "backup"  :  "",
            "backup1" :  "",
            "update"  :  update,
            "status"  :  loader,
        })
        self.sort_intervals()

    # Generates correct timing for intervals
    def sort_intervals(self):
        smallest = lambda x: x["time"]
        sort = sorted(self.intervals, key=smallest)
        self.smallest_interval = min(sort, key=smallest)
        self.time_interval = self.smallest_interval["time"]
        for interval in self.intervals:
            interval["increment_on"] = int(round(interval["time"] / self.time_interval))
            interval["backup"] = "" # This is an important thing to change/remember

    # Parses interval output according to its statuses
    def parse_interval_output(self, interval):
        try:
            if self.counter % interval["increment_on"] == 0:
                output = interval["function"]()
                interval["backup"] = interval["backup1"]
                interval["backup1"] = output
            else:
                output = interval["backup"]
        except draftlog.Exception:
            output = interval["backup"]
            interval["status"] = False

        return str(output)

    # What actually updates the LogDraft lines.
    def run_intervals(self):
        for interval in self.intervals:
            text = self.parse_interval_output(interval)
            if interval["update"] == True:
                interval["logdraft"].update(text)
            else:
                if text != interval["backup"] and text != "":
                    if interval.get("overwritten_init_line") != True:
                        interval["logdraft"].update(text)
                        interval["overwritten_init_line"] = True
                    else:
                        self.lcs.write(ansi.clearline)
                        print (text)

    # Checks if all intervals are done.
    def check_done(self):
        return all(x["status"] in (False, None) for x in self.intervals)

    # The actual running loop for updating intervals.
    def run(self):
        lines = 0
        while self.check_done() == False:
            self.counter += 1
            self.run_intervals()
            time.sleep(self.time_interval)
        self.lcs.write(ansi.clearline)
        sys.exit()

"""
Pretty much just a wrapper for "DaemonDrafter".
It's what the user actually interacts with and what
"draftlog.inject()" returns.
"""
class Drafter:
    def __init__(self):
        self.daemon_drafter = DaemonDrafter()

    def log(self, *args, **kwargs):
        logdraft = self.daemon_drafter.log(*args, **kwargs)
        return logdraft

    def start(self):
        self.daemon_drafter.start()