import argparse
import itertools
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from more_itertools import grouper
from tqdm import tqdm

_RE_PERC = re.compile(r"(?<!(\-|\+|\())\d{1,3}\.\d{2}\%")
_RETRY_SLEEP = 5


def build_metadata(subset="combined", reset_file=False, year_start=2004, year_end=2022):
    """Find a snapshot link for each month and save it in a metadata file."""
    metadata_path = Path.cwd() / f"metadata_{subset}.csv"
    df_cols = ["date_code", "archive_url", "file_name"]
    if not metadata_path.exists() or reset_file:
        df = pd.DataFrame(list(), columns=df_cols)
        df.to_csv(metadata_path, index=False)
    metadata = pd.read_csv(metadata_path, dtype=str)
    payload = {"url": None, "timestamp": None}
    base_url_platform = "https://store.steampowered.com/hwsurvey?platform="

    for year, month in (
        pbar := tqdm(itertools.product(range(year_start, year_end), range(1, 13)))
    ):
        date_code = f"{year}{month:02d}"
        num_retry = 1
        if metadata["date_code"].isin([date_code]).any():
            # url_available = metadata.loc[
            #     metadata["date_code"] == date_code, "archive_url"
            # ].to_numpy()[0]
            continue

        if year < 2009 and subset == "combined":
            payload.update({"url": "http://www.steampowered.com/status/survey.html"})
        elif subset == "combined":
            payload.update({"url": "https://store.steampowered.com/hwsurvey"})
        else:
            payload.update({"url": f"{base_url_platform}{subset}"})

        # query for mid-month to avoid getting snapshots for the next or previous month
        payload.update({"timestamp": f"{date_code}15"})
        # TODO: implement retry procedure
        r = requests.get("http://archive.org/wayback/available", params=payload)
        while not r.json()["archived_snapshots"]:
            time.sleep(_RETRY_SLEEP * num_retry)
            r = requests.get("http://archive.org/wayback/available", params=payload)
            num_retry += 1

        r_snapshot = r.json()["archived_snapshots"]["closest"]

        # check the snapshot is from the month and year we want
        payload_ts = datetime.strptime(payload["timestamp"], "%Y%m%d")
        snapshot_ts = datetime.strptime(r_snapshot["timestamp"], "%Y%m%d%H%M%S")
        if (payload_ts.month == snapshot_ts.month) & (
            payload_ts.year == snapshot_ts.year
        ):
            new_data = [date_code, r_snapshot["url"], f"{r_snapshot['timestamp']}.txt"]
        else:
            new_data = [date_code, None, None]

        # add retrieved snapshots to keep track of the downloaded periods
        curr_df = pd.DataFrame([new_data], columns=df_cols)
        curr_df.to_csv(metadata_path, mode="a", index=False, header=False)
        pbar.set_postfix(
            {"query": payload["timestamp"], "snaphsot": r_snapshot["timestamp"]}
        )
        time.sleep(_RETRY_SLEEP)


def download_web_content(save_path, subset="combined", overwrite=False):
    """Save the webpage content to a local file for faster inspection and iteration"""
    metadata = pd.read_csv(Path.cwd() / f"metadata_{subset}.csv")
    content_path = save_path / subset
    if not content_path.exists():
        content_path.mkdir(parents=True)

    for row in (pbar := tqdm(metadata.itertuples(), total=metadata.shape[0])):
        if pd.isna(row.archive_url):
            continue
        if not (content_path / row.file_name).exists() or overwrite:
            r = requests.get(row.archive_url)
            # save content to local for faster iteration and testing
            with open(content_path / row.file_name, "w") as f:
                f.write(r.text)
            pbar.set_postfix({"date_code": row.date_code, "subset": subset})
            time.sleep(3)


def old_parser(soup, agg_ram=False):
    """Retrieve information from the different categories with old web style."""
    data_json = {}
    cat_tree = soup.find_all("div", class_=re.compile("capsule|capcontent"))
    for tree in cat_tree:
        name = tree.find("b")
        data_json[name.text.strip()] = {}

        content = tree.find("table").find_all("td", {"align": "right"})
        cols = 4 if name.text.strip() == "RAM" and agg_ram else 3
        for left, mid, *right in grouper(content, cols, fillvalue=None):
            item = left.text.strip()
            right, *_ = right
            value = float(right.text.strip("%"))
            data_json[name.text.strip()][item] = value
    return data_json


def modern_parser(soup):
    """Retrieve information from the different categories with present web style."""
    data_json = {}
    cat_tree = soup.find_all(
        "div", {"id": re.compile(r"(cat\d{1,}|osversion)_details")}
    )
    cat_title = soup.find_all(
        "div",
        {
            "id": re.compile(r"(cat\d{1,}|osversion)_stats_row"),
            "onclick": re.compile("toggleRow(.+)"),
        },
    )
    for tree, title in zip(cat_tree, cat_title):
        name = title.find("div", class_="stats_col_left")
        data_json[name.text.strip()] = {}

        cat_class = re.compile(r"stats_col_(left|left_holder|mid|mid_details|right)\b")
        cat_groups = grouper(tree.find_all("div", class_=cat_class), 3, fillvalue=None)
        for left, mid, right in cat_groups:
            item = left.text.strip() if left.text.strip() else mid.text.strip()
            value = re.search(_RE_PERC, right.text)
            value = float(value.group(0).strip("%"))
            # build extra category for aggregates
            if item in ["Windows", "OSX", "Linux"]:
                # sometimes Linux appears as a distro instead of an aggregate
                # 'Windows' category is the only one to init the dict
                if item == "Windows":
                    if "OS Version (total)" not in data_json:
                        data_json["OS Version (total)"] = {}
                    data_json["OS Version (total)"][item] = value
                else:
                    if "OS Version (total)" not in data_json:
                        data_json[name.text.strip()][item] = value
                    else:
                        data_json["OS Version (total)"][item] = value
            else:
                data_json[name.text.strip()][item] = value
    return data_json


def parse_data_content(save_path, subset="combined"):
    """Parse and extract file contents and save them in a JSON file."""
    steam_hw_survey = []
    metadata = pd.read_csv(Path.cwd() / f"metadata_{subset}.csv", dtype=str)
    metadata = metadata.dropna(subset=["file_name"])
    metadata["date"] = pd.to_datetime(metadata["date_code"], format="%Y%m")
    metadata["year"] = metadata["date"].dt.year
    metadata["month"] = metadata["date"].dt.month
    content_path = save_path / subset

    for row in (pbar := tqdm(metadata.itertuples(), total=metadata.shape[0])):
        data = open(content_path / row.file_name).read()
        soup = BeautifulSoup(data, "html.parser")
        data_dict = {}
        if (row.year == 2008 and row.month == 12) or row.year > 2008:
            data_dict = modern_parser(soup)
        else:
            # during this period a 4th column with aggregate data is added for the "RAM" category
            agg_ram = True if row.year == 2005 and row.month > 7 else False
            data_dict = old_parser(soup, agg_ram)
        if data_dict:
            data_dict["date_code"] = row.date_code
            steam_hw_survey.append(data_dict)
        pbar.set_postfix({"date_code": row.date_code, "subset": subset})
    with open(Path.cwd() / f"survey_data_{subset}.json", "w") as f:
        json.dump(steam_hw_survey, f, indent=2)


def clean_and_normalize(subset="combined"):
    df_list = []
    data_path = Path.cwd() / f"survey_data_{subset}.json"
    if not data_path.exists():
        raise f"{data_path}: file not found, check you have parsed the content for this subset and the JSON file exists."

    with open(data_path) as f:
        data = json.loads(f.read())

    for item in (pbar := tqdm(data)):
        pbar.set_postfix({"date_code": item["date_code"], "subset": subset})
        for cat in item.keys():
            if cat not in ["date_code"]:
                cat_data = itertools.zip_longest(
                    list(item[cat].values()), [cat], fillvalue=cat
                )
                df = json.dumps(
                    {
                        "columns": ["perc", "category"],
                        "index": list(item[cat].keys()),
                        "data": list(cat_data),
                    }
                )
                df = pd.read_json(df, orient="split")
                df["date"] = datetime.strptime(str(item["date_code"]), "%Y%m")
                df["platform"] = subset
                df_list.append(df)
    df = pd.concat(df_list, axis=0)
    df.reset_index(inplace=True)

    # clean category titles
    df["category"] = df["category"].replace(
        to_replace=r"\s{1,}\(.+(?<!total)\).*$", value="", regex=True
    )
    df["category"] = df["category"].astype("category")
    df["index"] = df["index"].replace(to_replace=r"\&lt", value="<", regex=True)

    # rename categories for consistency
    cat_rename = {
        "RAM": "System RAM",
        "Processor Count": "Physical CPUs",
        "FreeHD": "Free Hard Drive Space",
        "TotalHD": "Total Hard Drive Space",
        "DirectX10 Systems": "DirectX 10 Systems",
    }
    df["category"] = df["category"].replace(cat_rename)
    df["category"] = df["category"].astype("category")

    # early hw surveys where Windows only despite the general URL
    if subset=="combined":
        df.loc[df["date"] < "2010-06-01", "platform"] = "pc"
    df["platform"] = df["platform"].astype("category")

    # df.to_csv(f"steam_hw_survey_{subset}.csv", index=False)
    df.to_parquet(f"steam_hw_survey_{subset}.parquet", index=False)
    

def parse_current_month(subset="combined"):
    if subset == "combined":
        payload = {}
    else:
        payload = {"platform": subset}
    base_url = "https://store.steampowered.com/hwsurvey"
        
    r = requests.get(base_url, params=payload)
    soup = BeautifulSoup(r.text, "html.parser")
    data_dict = modern_parser(soup)
    steam_hw_survey = []
    if data_dict:
        data_dict["date_code"] = datetime.today().strftime("%Y%m")
        steam_hw_survey.append(data_dict)
    with open(Path.cwd() / f"survey_data_{subset}.json", "w") as f:
        json.dump(steam_hw_survey, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Steam's survey data.")
    parser.add_argument(
        "--save_path",
        help="Path where the downloaded content will be saved.",
        default=Path.cwd(),
        type=str,
    )
    parser.add_argument(
        "--subset",
        help="Platform subsets to process.",
        choices=["all", "combined", "pc", "mac", "linux"],
        type=str,
    )
    parser.add_argument(
        "--process",
        help="Process to run.",
        choices=[
            "build_metadata",
            "download_content",
            "parse_content",
            "generate_output",
            "parse_current_month",
        ],
        type=str,
    )
    args = parser.parse_args()

    platform_year_start = {
        "combined": 2004,
        "pc": 2010,
        "mac": 2010,
        "linux": 2014,
    }

    subset = [args.subset]
    if args.subset == "all":
        subset = ["combined", "pc", "mac", "linux"]

    for subset_ in subset:
        if args.process == "build_metadata":
            build_metadata(subset=subset_, year_start=platform_year_start[subset_])
        elif args.process == "download_content":
            download_web_content(args.save_path, subset=subset_)
        elif args.process == "parse_content":
            parse_data_content(args.save_path, subset=subset_)
        elif args.process == "generate_output":
            clean_and_normalize(subset=subset_)
        elif args.process == "parse_current_month":
            parse_current_month(subset=subset_)
            time.sleep(_RETRY_SLEEP)

    if args.subset == "all" and args.process == "generate_output":
        if Path("steam_hw_survey_old.parquet").exists():
            subset.append("old")
        df = pd.concat([pd.read_parquet(f"steam_hw_survey_{x}.parquet") for x in subset])
        df.to_parquet("steam_hw_survey.parquet", index=False)
