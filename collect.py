import csv
import sys
import argparse
import datetime
from subprocess import check_output


class Commit:
    @staticmethod
    def from_csv_file(filename: str) -> list['Commit']:
        """Load commits from a CSV file."""
        commits = []
        with open(filename, 'r') as f:
            csv_reader = csv.reader(f)
            next(csv_reader)  # Skip header
            for row in csv_reader:
                repository, sha, timestamp, author, added, removed = row
                dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                added = int(added)
                removed = int(removed)
                commits.append(Commit(repository=repository, sha=sha, timestamp=dt, author=author, commits=1, added=added, removed=removed))
        return commits

    def __init__(self, repository: str, sha: str, timestamp: datetime.datetime, author: str, commits: int, added: int = -1, removed: int = -1):
        self.repository = repository
        self.sha = sha
        self.timestamp = timestamp
        self.author = author
        self.added = added
        self.removed = removed

    def __repr__(self):
        return f"Commit(sha={self.sha}, timestamp={self.timestamp}, author={self.author}, commits={self.commits}, added={self.added}, removed={self.removed})"

    def to_csv_row(self):
        return [
            self.repository,
            self.sha,
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            self.author,
            self.added,
            self.removed
        ]

    def update(self, added: int, removed: int):
        self.added = added
        self.removed = removed



def get_commits(repository_path: str):
    repo = repository_path.split("/")[-1]
    sys.stdout.write(f"collecting the commits of {repo}\n")
    
    args = ["git", "-C", repository_path, "log", "--pretty=format:%H|%at|%an", "--reverse"]
    # git log --pretty=format:"%H|%at|%an" --reverse
    # output format:
    # c6370125df4e999f365eda516831465eede59396|1636063992|danielmoessner

    items = []
    for o in check_output(args, universal_newlines=True, shell=False).split("\n"):
        c = o.split("|")
        sha = c[0]
        dt = datetime.datetime.fromtimestamp(int(c[1]))
        author = c[2]
        items.append(Commit(repository=repo, sha=sha, timestamp=dt, author=author, commits=1, added=-1, removed=-1))

    return items


def add_line_stats(items: list[Commit], repository: str) -> list[Commit]:
    def get_added_removed(item: Commit, repository: str) -> Commit:
        args = ["git", "-C", repository, "show", "--numstat", item.sha]
        output = check_output(args, universal_newlines=True, shell=False)

        added = 0
        removed = 0
        for line in output.split("\n"):
            if line.strip() == "":
                continue
            parts = line.split("\t")
            if len(parts) == 3:
                added += int(parts[0]) if parts[0] != "-" else 0
                removed += int(parts[1]) if parts[1] != "-" else 0

        return added, removed

    repo = repository.split("/")[-1]
    sys.stdout.write(f"adding line stats for {len(items)} commits in {repo}\n")
    for item in items:
        item.update(*get_added_removed(item, repository))
    return items


def save_commits(commits: list[Commit], filename: str):
    with open(filename, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(['Repository', 'SHA', 'Timestamp', 'Author', 'Added', 'Removed'])
        for commit in commits:
            csv_writer.writerow(commit.to_csv_row())


def main():
    p = argparse.ArgumentParser(description="Collects git commit data from one or more repositories.")
    p.add_argument("repositories", action="store", type=str, nargs="+", help="one or more repository paths")
    p.add_argument("-o", "--output", dest="output", action="store", type=str, default="commits.csv", help="output csv file name")
    args = p.parse_args()
    commits = []
    for r in args.repositories:
        rcommits = get_commits(r)
        add_line_stats(rcommits, r)
        commits.extend(rcommits)
    save_commits(commits, args.output)


if __name__ == "__main__":
    main()