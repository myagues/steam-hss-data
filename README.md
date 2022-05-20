# Steam Hardware & Software Survey Dataset

> Every few months we run a hardware survey on Steam. If you participate, the survey collects data about what kinds of computer hardware and system software you're using, and the results get sent to Steam. The survey is incredibly helpful for us as game developers in that it ensures that we're making good decisions about what kinds of technology investments to make, and also gives people a way to compare their own current hardware setup to that of the community as a whole.
>
> _Steam Hardware Survey ~ 2007_

__Note: this dataset uses snapshots and an API from the [Wayback Machine](https://web.archive.org), a free service that relies on donations. If you find this data useful, consider making a [donation](https://archive.org/donate/?origin=wbwww-HomeDonateButton).__

## Contents

- [Description](#desc)
- [Installation](#inst)
- [Building the dataset](#dataset-build)
- [Survey modification over the years](#survey-evo)
- [Survey notifications](#survey-not)
- [References](#refs)

<a name="desc" />

## Description

This repository provides the scripts for collecting historical data from the [Steam Hardware & Software Survey](https://store.steampowered.com/hwsurvey). Since 2004 (the first snapshot available in the Wayback Machine), Steam provides data from users that voluntarily take part in the survey, and updates the results on a monthly schedule. Using the service provided by the [Wayback Machine](https://web.archive.org), we can find old snapshots, providing data at different points in time, and tracing the full picture of hardware trends in the Steam user base. Unfortunately, some months are missing from the archives of the Wayback Machine, but enough are available for building an interesting dataset.

The front-end of the page has been changing over the years, and categories displayed have been appearing and disappearing, depending on technology trends or page format. Since it is a running process over almost [two decades](https://arstechnica.com/uncategorized/2004/09/4233-2), spanning a wide range of different systems, some reporting errors have been solved over time, but some cleaning still needs to be done when working with the dataset. This repository relies on two different parsers, for the old version of the survey and the current one, that extract data from different categories and platforms, and save it with [long-form](https://seaborn.pydata.org/tutorial/data_structure.html#long-form-vs-wide-form-data) in a [Parquet](https://parquet.apache.org/documentation/latest) file.

In the [Releases](https://github.com/myagues/steam-hss-data/releases) category you will find a file that contains all the data extracted from the Wayback Machine up until setting up this repo, [2021.12](https://github.com/myagues/steam-hss-data/releases/tag/2021.12), so you do not need to rebuild the dataset for using it, unless you want to make changes to the extraction procedures.

With [GitHub Actions](https://github.com/features/actions) new data gets added to the [latest](https://github.com/myagues/steam-hss-data/releases/tag/latest) release, containing data from the Wayback Machine and up to date values extracted from the web.

You can also explore the Jupyter Notebook with [Google Colab](https://colab.research.google.com/). If you are more comfortable with JS, you can load the dataset in [Observable](https://observablehq.com) and do some [exploration](https://observablehq.com/@myagues/trends-from-the-steam-hardware-software-survey).

[![Open data in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/myagues/steam-hss-data/blob/main/plot_categories_example.ipynb)

<a name="inst" />

## Installation

This repository requires Python v3.8 minimum, and Jupyter to run the notebook:

```bash
$ git clone https://github.com/myagues/steam-hss-data
$ cd steam-hss-data
$ pip install -r requirements.txt
```

<a name="dataset-build" />

## Building the dataset

Collecting the dataset is divided in four steps:

- __Retrieve snapshots available for each month__

```bash
$ python main.py --subset=all --process=build_metadata
```

This will generate CSV files for each platform and are already provided in the repository.

- __Download snapshot content to local__

```bash
$ python main.py --subset=all --process=download_content
```

Snapshot content will be saved to local drive (`--save_path`).

- __Extract and save the page content in a JSON file__

```bash
$ python main.py --subset=all --process=parse_content
```

Content for each platform will be saved in JSON files to easily inspect categories and results of the extraction.

- __Clean and normalize to a Parquet file__

```bash
$ python main.py --subset=all --process=generate_output
```

JSON files will be parsed and results will be saved in Parquet files.

__Note: `date` column shows the month of the snapshot, which is generally the month after the data was taken.__


<a name="survey-evo" />

## Survey modifications over the years

__v1.0 - from April 2004__

  - URL: http://www.steampowered.com/status/survey.html
  - Sample size and user quantities displayed
  - Data collection runs periodically (e.g. _This survey began on August 9th, 2005. This page last updated: 6:30pm PST (02:30 GMT), September 15 2005_)
  - Page was not updated monthly (e.g. December 2005 reporting results for September that year)
  - Some of the categories displayed change over the years

__v1.1 - from December 2007__

  - Content and displayed information remains the same, just a cosmetic update
  - Change in the time frame of data collecting. Instead of doing a periodic sampling, they do a rolling update (e.g. _This survey began November 13th, 2007. Last updated: 3:53am PST (11:53 GMT), November 04 2008_)
  - Page updated randomly, sometimes multiple times per month or no update in a whole month (e.g. September 2007)

__v2.0 - from mid-December 2008__

  - URL: http://store.steampowered.com/hwsurvey
  - Major page overhaul with first charts, but sample size and quantity information not shown, and time-frame of the survey disappears
  - We have to assume that from this point forward the sampling is on a monthly basis, given the change in the description from _Every few months we run a hardware survey on Steam_ to _Each month, Steam collects data about [...]_, and the fact that time-frame information gets removed

__v3.0 - from mid-May 2010__

  - Addition of Mac information, with some charts and the possibility to filter categories by Windows, Mac or combined platforms
  - Old categories are moved to the __Windows only__ tab
  - From September 2010, addition of software information for Windows platform, although data is not updated on a monthly schedule (time freezed at July 2010)

__v3.1 - from mid-December 2011__

  - Charts are rendered with Adobe Flash (you can still browse the content, although charts will not be displayed)
  - From April 2013 the Windows software list disappears, after not having been ever updated

__v3.2 - from February 2014__

  - Linux platform statistics filter is added
  - From June 2016 Adobe Flash charts are no more

<a name="survey-not" />

## Survey notifications

__May 2012__

> Why do many of the Steam Hardware Survey numbers seem to undergo a significant change in April 2012?
>
> There was a bug introduced into Steam's survey code several months ago that caused a bias toward older systems. Specifically, only systems that had run the survey prior to the introduction of the bug would be asked to run the survey again. This caused brand new systems to never run the survey. In March 2012, we caught the bug, causing the survey to be run on a large number of new computers, thus giving us a more accurate survey and causing some of the numbers to vary more than they normally would month-to-month. Some of the most interesting changes revealed by this correction were the increased OS share of Windows 7 (as Vista fell below XP), the rise of Intel as a graphics provider and the overall diversification of Steam worldwide (as seen in the increase of non-English language usage, particularly Russian).

__February 2018__

> STEAM HARDWARE SURVEY FIX – 5/2/2018
>
> The latest Steam Hardware Survey incorporates a number of fixes that address over counting of cyber cafe customers that occurred during the prior seven months.
>
> Historically, the survey used a client-side method to ensure that systems were counted only once per year, in order to provide an accurate picture of the entire Steam user population. It turns out, however, that many cyber cafes manage their hardware in a way that was causing their customers to be over counted.
>
> Around August 2017, we started seeing larger-than-usual movement in certain stats, notably an increase in Windows 7 usage, an increase in quad-core CPU usage, as well as changes in CPU and GPU market share. This period also saw a large increase in the use of Simplified Chinese. All of these coincided with an increase in Steam usage in cyber cafes in Asia, whose customers were being over counted in the survey.
>
> It took us some time to root-cause the problem and deploy a fix, but we are confident that, as of April 2018, the Steam Hardware Survey is no longer over counting users.

<a name="refs" />

## References

- Colin Luoma, [_Historical Linux Statistics from Steam's Hardware & Software Survey_](https://www.cluoma.com/?page=blog&id=51), [[GitHub]](https://github.com/cluoma/steam_hws_scraper)
