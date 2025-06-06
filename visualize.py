import statistics
import sys
import argparse
import datetime
from collections import OrderedDict
from functional import list_filter, list_map, list_reduce
from collect import Commit


class Group:
    def __init__(self, name: str, commits: list[Commit]):
        self.name = name
        self.commits = commits

    @property
    def added(self):
        return sum(item.added for item in self.commits)
    
    @property
    def removed(self):
        return sum(item.removed for item in self.commits)
    
    @property
    def change(self):
        return self.added + self.removed
    
    def get_score(self, minv: int, maxv: int) -> float:
        if self.change < minv:
            return 0
        if self.change > maxv:
            return 1
        if maxv - minv == 0:
            return 0
        return (self.change - minv) / (maxv - minv)


class Day:
    @staticmethod
    def _fill_missing_dates(days: OrderedDict[datetime.date, 'Day']) -> OrderedDict[datetime.date, 'Day']:
        if not days:
            return days
        
        min_date = min(days.keys())
        max_date = max(days.keys())
        
        current_date = min_date
        while current_date <= max_date:
            if current_date not in days:
                days[current_date] = Day(current_date, [])
            current_date += datetime.timedelta(days=1)
        
        return days

    @staticmethod
    def from_commits(commits: list[Commit]) -> OrderedDict[datetime.date, 'Day']:
        days: OrderedDict[datetime.date, Day] = OrderedDict()
        for commit in commits:
            date = commit.timestamp.date()
            if date not in days:
                days[date] = Day(date, [])
            days[date].commits.append(commit)

        days = Day._fill_missing_dates(days)

        return days

    def __init__(self, date: datetime.date, commits: list[Commit]):
        self.date =  date
        self.commits = commits
        self.score = 0

    def __repr__(self):
        return f"Day(date={self.date}, commits={list(map(lambda x: x.sha, self.commits))}, score={self.score})"


def normalize(x, xmin, xmax):
    """Normalize a number to a 0-1 range given a min and max of its set."""
    return float(x - xmin) / float(xmax - xmin)





def fill_dates(data):
    """Fill missing dates where there were no commits."""
    n = len(data)
    i = 0
    while i < n - 1:
        cur = data[i].timestamp
        if (data[i+1].timestamp - cur).days > 1:
            data.insert(i+1, Commit(
                timestamp=cur + datetime.timedelta(days=1),
                is_weekend=cur.weekday() > 4
            ))
            n += 1
        i += 1


def print_items(items: list[Commit]):
    for i in items:
        print(f"{i.timestamp.strftime('%Y-%m-%d %a')} {i.author} added {i.added} and removed {i.removed}")


def calculate_scores(items: OrderedDict[datetime.date, Day]):
    """compute normalized scores (0-1)"""
    vals = [items[i].change for i in items]
    vals.append(0)

    xmin = min(vals)
    xmax = max(vals)

    for i in items.values():
        i.set_score(xmin, xmax)



def build_bars(groups: dict[str, Group], stddev_range: tuple[float, float, float], block=u"\u2580", width=50) -> list[str]:
    bars = []
    _, lower, upper = stddev_range
    for name in sorted(groups.keys()):
        group = groups[name]
        bar = ""
        bar += (group.name)
        bar += ("  ")
        bar += (str(group.change))
        bar += ((5 - len(str(group.change))) * " ")
        bar += (block * int(group.get_score(lower, upper) * width))
        bar += ("\n")
        bars.append(bar)
    return bars


def filter_by_authors(commits: list[Commit], authors: list[str]) -> list[Commit]:
    _authors = list_map(authors, lambda a: a.strip().lower())
    filtered_commits = list_filter(commits, lambda x: x.author.strip().lower() in _authors)
    sys.stdout.write(f"\n=> filtered down from {len(commits)} to {len(filtered_commits)} commits\n")
    return filtered_commits


def get_authors(commits: list[Commit]):
    def update(authors: dict[str, int], commit: Commit) -> dict[str, int]:
        authors.setdefault(commit.author, 0)
        authors[commit.author] += 1
        return authors
    authors = list_reduce(commits, update, {})
    authors_ordered = OrderedDict(sorted(authors.items(), key=lambda x: x[1], reverse=True))
    return authors_ordered


def group_by_week(commits: list[Commit]) -> dict[str, Group]:
    def update(groups: dict[str, Group], commit: Commit) -> dict[str, Group]:
        week = commit.timestamp.strftime("%Y-%W")
        if week not in groups:
            groups[week] = Group(week, [])
        groups[week].commits.append(commit)
        return groups
    groups = list_reduce(commits, update, {})
    sys.stdout.write(f"\n=> grouped into {len(groups)} weeks\n")
    return groups


def get_stddev_range(groups: dict[str, Group]) -> tuple[float, float, float]:
    changes = list_map(groups.values(), lambda g: g.change)
    if not changes:
        return None, None, None
    mean = round(statistics.mean(changes))
    stddev = round(statistics.stdev(changes)) if len(changes) > 1 else 0
    lower = max(round(mean - stddev), 0)
    upper = round(mean + stddev)
    sys.stdout.write(f"\n=> calculated the stddev\n")
    sys.stdout.write(f"mean: {mean}, lower: {lower}, upper: {upper}\n")
    return mean, lower, upper


def write_bars_to_file(bars: list[str], filename: str):
    with open(filename, 'w') as f:
        for bar in bars:
            f.write(bar)
    sys.stdout.write(f"\n=> wrote bars to {filename}\n")


def main():
    p = argparse.ArgumentParser(description="Shows git commit count bars.")
    p.add_argument("-i", "--input", dest="file", action="store", type=str, help="file with the commits data")
    p.add_argument("-a", "--author", action="store", dest="authors",
                   nargs="*",
                   type=str, required=False, default=[],
                   help="filter by author github names")
    p.add_argument("-o", "--output", dest="output", action="store", type=str, default="bars.txt",)
    args = p.parse_args()

    commits = Commit.from_csv_file(args.file)

    authors = get_authors(commits)
    sys.stdout.write(f"=> found {len(authors)} authors\n")
    for author, count in authors.items():
        sys.stdout.write(f"{author}: {count}\n")

    commits = filter_by_authors(commits, args.authors)

    weeks = group_by_week(commits)
    mean, lower, upper = get_stddev_range(weeks)
    
    bars = build_bars(weeks, (mean, lower, upper))
    write_bars_to_file(bars, args.output)


if __name__ == "__main__":
    main()
