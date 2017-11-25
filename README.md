# Code Metriker

Code metrics are often used to please the management.  The project started with
an analysis of which metrics are helpful and which are not. These metrics
include Lines of Code because it represents a quantitative progression. A
really helpful metric is Cyclomatic Complexity, it helps to find highly
nested/branched constructs. Besides this metric, the functional length is not
to be neglected: small maintainable functions increase the overview and reduce
errors.

## Screenshot


![Screenshot](https://github.com/hgn/code-metriker/raw/master/docs/screenshot-cc.png)

# Setup and Run

## Setup

Install required dependencies via pip:

```
sudo pip3 install -r requirements.txt
```

> Note: all required packages are also available via Debian package manager
> (aptitude).


## Run

```
sudo ./run.py -f conf/code-metriker.conf
```
