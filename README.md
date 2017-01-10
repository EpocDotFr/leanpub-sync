# Leanpub library synchronization

Tired to manually download every single book from your [Leanpub](https://leanpub.com/) library to your e-reader? I got you covered.

## Prerequisites

Python 3. May eventually works with Python 2 (not tested).

## Installation

Clone this repo, and then the usual `pip install -r requirements.txt`.

## Configuration

Copy the `.env.example` file to `.env` and fill in the configuration parameters.

Available configuration parameters are:

  - `LEANPUB_EMAIL` Leanpub account email
  - `LEANPUB_PASSWORD` Leanpub account password
  - `LEANPUB_PREFERED_FORMAT` Format of the books to download. May be `epub` (for reading on phones and tablets), `pdf` (for reading on a computer) or `mobi` (for reading on a Kindle). Will automatically download an alternative version if your prefered isn't available
  - `OUTPUT_DIR` Directory in which to download the books (relative or absolute)

## Usage

```
python run.py
```

## How it works

Please refer to the script itself (`run.py`), it is self-explanatory.