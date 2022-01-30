# -*- coding: utf-8 -*-
"""Python script that calls stackoverflow's API."""
import datetime
import re
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import requests

URL = "https://api.stackexchange.com/2.2/questions"
DATE = datetime.datetime.utcnow().date()
ROOT = Path(__file__).resolve().parent
JSON = Dict[str, Any]
Params = Dict[str, Union[str, int]]
Timestamps = Tuple[int, int]


def get_epochs(date: datetime.date, offset_days: int = 1) -> Timestamps:
    """Get epoch dates for the start and end of the date."""
    offset_date = date - datetime.timedelta(days=offset_days)
    start = datetime.datetime(
        year=offset_date.year,
        month=offset_date.month,
        day=offset_date.day,
        hour=0,
        minute=0,
        second=0,
    )
    end = datetime.datetime(
        year=date.year, month=date.month, day=date.day, hour=23, minute=59, second=59
    )
    return int(start.timestamp()), int(end.timestamp())


def fetch_questions(
    start: int,
    end: int,
    tags: str,
    site: str = "stackoverflow",
    votes_threshold: int = 1,
) -> JSON:
    """Fetch questions from stack exchange API.


    Parameters
    ----------
    start, end : int, epoch timestamps
        Correspond to fromdate and todate API params and are inclusive
    tags : str, tag(s) to look for
        might take up to 5 tags using AND operator : "pandas;numpy"
    site : str
        stackexchange site to fetch questions from, defaults to 'stackoverflow'
    votes_threshold : int
        min number of votes a question should have, defaults to 1
    """
    params: Params = {
        "fromdate": start,
        "todate": end,
        "order": "desc",
        "sort": "votes",
        "min": votes_threshold,
        "tagged": tags,
        "site": site,
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    data: JSON = response.json()
    return data


def format_item(item: JSON) -> str:
    """Format entry."""
    title = re.sub(r"[^\w\s]", "", item["title"])
    return f"* [{title}]({item['link']}) - {item['score']} votes"


def build_column(data: JSON, limit: int = 5) -> str:
    """Build an unordered markdown list from a list of entries."""
    return "\n".join(map(format_item, data["items"][:limit]))


def replace_chunk(
    content: str,
    chunk: str,
    tags: str,
    inline: bool = True,
) -> str:
    """Replace chunks of README.md"""
    pattern = re.compile(
        rf"<!-- {tags} starts -->.*<!-- {tags} ends -->",
        re.DOTALL,
    )
    if not inline:
        chunk = f"\n{chunk}\n"
    chunk = rf"<!-- {tags} starts -->{chunk}<!-- {tags} ends -->"
    return pattern.sub(chunk, content)


if __name__ == "__main__":
    readme = ROOT / "README.md"
    readme_contents = readme.open(encoding="utf-8").read()
    rewritten_readme = replace_chunk(readme_contents, DATE.strftime("%Y-%m-%d"), "date")

    for tag in ["python", "fastapi", "pandas"]:
        start_ts, end_ts = get_epochs(DATE)
        questions = fetch_questions(start_ts, end_ts, tag)
        formatted_column = build_column(questions)
        rewritten = replace_chunk(rewritten_readme, formatted_column, tag, inline=False)
        with open(readme, "w", encoding="utf-8") as output:
            output.write(rewritten_readme)
