import re
import datetime
import requests
import sqlite_utils
from pathlib import Path
from typing import Any, Dict, List, Tuple


URL = "https://api.stackexchange.com/2.2/questions"
DATE = datetime.datetime.utcnow().date()
ROOT = Path(__file__).resolve().parent


def get_epochs(
    date: datetime.datetime, 
    offset_days: int = 0,
    **kwargs
) -> Tuple[int]:    
    """ Get epoch dates for the start and end of the date. """
    
    offset_date = date - datetime.timedelta(days=offset_days)
    start = datetime.datetime(
        year=offset_date.year, month=offset_date.month, day=offset_date.day,
        hour=0, minute=0, second=0
    )
    end = datetime.datetime(
        year=date.year, month=date.month, day=date.day,
        hour=23, minute=59, second=59
    )
    return int(start.timestamp()), int(end.timestamp())


def fetch_questions(
    start: int, 
    end: int, 
    tags: str, 
    site: str = "stackoverflow", 
    votes_threshold: int = 1,
    **kwargs
) -> Dict[str, Any]:
    """ Fetch questions from stack exchange API. 
    
    
    Parameters
    ----------
    start, end : int, epoch timestamps
        Correspond to fromdate and todate API params and are inclusive
    tags : str, tag(s) to look for
        might take up to 5 tags using AND operator : "pandas;numpy"
    site : str 
        stackexchange site to fetch questions from 
    votes_threshold : int 
        min number of votes a question should have
    """

    params = {
        "fromdate": start,
        "todate": end,
        "order": "desc",
        "sort": "votes",
        "min": votes_threshold,
        "tagged": tags,
        "site": site,
    }
    r = requests.get(URL, params=params)
    r.raise_for_status()
    return r.json()


def format_item(item: Dict[str, Any]) -> str:
    """ Format entry. """
    
    title = re.sub(r"[^\w\s]", "", item["title"])
    return f"* [{title}]({item['link']}) - {item['score']} votes"


def build_column(data: List[Dict[str, Any]]) -> str:
    """ Build an unordered markdown list from a list of entries. """
    return "\n".join(map(format_item, data["items"][:5]))


def replace_chunk(
    content: str, chunk: str, tags: str, inline: bool = False, **kwargs
) -> str:
    """ Replace chunks of README.md """
    
    r = re.compile(
        rf"<!-- {tags} starts -->.*<!-- {tags} ends -->",
        re.DOTALL,
    )
    if not inline:
        chunk = f"\n{chunk}\n"
    chunk = f"<!-- {tags} starts -->{chunk}<!-- {tags} ends -->"
    return r.sub(chunk, content)


def upsert_db(data: List[Dict[str, Any]]):
    """ update-or-insert questions to sqlite db. """
    questions = data["items"][:5]
    timestamp = f"{DATE:%Y-%m-%d %H:%M}"
    convert_epoch = datetime.datetime.utcfromtimestamp

    db = sqlite_utils.Database(ROOT / "stackoverflow.db")
    db["questions"].upsert_all(
            (
                {
                    "question_id": row["question_id"],
                    "title": row["title"],
                    "tags": ",".join(row["tags"]),
                    "owner_id": row["owner"]["user_id"],
                    "is_answered": row["is_answered"],
                    "view_count": row["view_count"],
                    "answer_count": row["answer_count"],
                    "score": row["score"],
                    "site": row["link"].split(".")[0].split("/")[-1],
                    "link": row["link"],
                    "creation_date": f'{convert_epoch(row["creation_date"]):%Y-%m-%d %H:%M}',
                    "inserted_date": timestamp
                }
                for row in questions
            ),
            pk="question_id"
        )

    db["users"].upsert_all(
            (
                {
                    "user_id": row["owner"]["user_id"],
                    "user_type": row["owner"]["user_type"],
                    "display_name": row["owner"]["display_name"],
                    "link": row["owner"]["link"],
                    "site": row["link"].split(".")[0].split("/")[-1],
                    "inserted_date": timestamp 
                }
                for row in questions
            ),
            pk="user_id"
        )


if __name__ == "__main__":
    
    readme = ROOT / "README.md"
    readme_contents = readme.open().read()
    rewritten = replace_chunk(
        readme_contents, DATE.strftime("%Y-%m-%d"), "date", inline=True
    )

    sections = (
        {"tags": "pandas", "site": "stackoverflow", "offset_days": 0},
        {"tags": "ggplot2", "site": "stackoverflow", "offset_days": 0},
        {"tags": "matplotlib", "site": "stackoverflow", "offset_days": 0}
    )

    for section in sections:
        start, end = get_epochs(DATE, **section)
        questions = fetch_questions(start, end, **section)
        content = build_column(questions)
        rewritten = replace_chunk(rewritten, content, **section)
        
        with open(readme, "w") as output:
            output.write(rewritten)

        upsert_db(questions)
        