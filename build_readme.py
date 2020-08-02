import re
import requests
from pathlib import Path
from datetime import datetime


URL = "https://api.stackexchange.com/2.2/questions"
DATE = datetime.utcnow().date()
ROOT = Path(__file__).parent.resolve()


def get_epochs(date):
    """ Get epoch dates for the start and end of the (current) day. """

    start = datetime(
        year=date.year, month=date.month, day=date.day,
        hour=0, minute=59, second=59
    )
    end = datetime(
        year=date.year, month=date.month, day=date.day,
        hour=23, minute=59, second=59
    )
    return int(start.timestamp()), int(end.timestamp())


def fetch_questions(start, end, tag, site="stackoverflow"):
    """ Fetch questions from stackoverflowAPI. """

    _params = {
        "fromdate": start,
        "todate": end,
        "order": "desc",
        "sort": "votes",
        "tagged": tag,
        "site": site,
    }
    return requests.get(URL, params=_params).json()


def build_table(*args, **kwargs):
    """ Build a markdown table from a list of entries. """

    columns = [
        "\n".join(
            "* [{title}]({url}) - {score} votes".format(
                title=re.sub(r'[^\w\s]', '', item["title"]),
                url=item["link"],
                score=item["score"]
            )
            for item in chunk["items"][:8]
        )
        for chunk in args
    ]
    return columns


def replace_chunk(content, marker, chunk, inline=False):
    """ Replace chunks of README.md """

    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


if __name__ == "__main__":
    
    readme = ROOT / "README.md"
    start, end = get_epochs(DATE)

    pandas, beautifulsoup, code_review = build_table(
        fetch_questions(start, end, tag="pandas"),
        fetch_questions(start, end, tag="beautifulsoup"),
        fetch_questions(start, end, tag="python", site="codereview")
    )

    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "date", DATE.strftime("%Y-%m-%d"), inline=True)
    rewritten = replace_chunk(rewritten, "pandas", pandas)
    rewritten = replace_chunk(rewritten, "bs", beautifulsoup)
    rewritten = replace_chunk(rewritten, "code_review", code_review)

    with open(readme, "w") as output:
        output.write(rewritten)