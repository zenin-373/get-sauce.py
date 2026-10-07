# get-sauce.py

Python implementation of a general-purpose downloader architecture inspired by the original Go project.

This independent implementation is intended for content you are authorized to download. It does not implement CAPTCHA bypass, DRM bypass, paywall bypass, or other access-control circumvention.

## Requirements
- Python 3.10+
- requests
- Optional FFmpeg for HLS streams

## Windows

    python -m pip install -r requirements.txt
    python get_sauce.py "https://example.com/file.mp4"

Or:

    run.bat "https://example.com/file.mp4"

## Options

    -i, --info       Inspect without downloading
    -j, --json       Print inspection data as JSON
    -F, --file       Read URLs from a text file
    -O, --output     Output directory
    -o, --name       Output filename for one URL
    -w, --workers    Concurrent download workers
    -T, --timeout    HTTP timeout in seconds
    -h, --header     Explicit HTTP request header
    -t, --truncate   Do not resume an existing file
    -q, --quiet      Minimal output
    -v, --version    Show version

Use only lawful/authorized URLs and respect site terms and access rules.

## Layout
- get_sauce.py
- requirements.txt
- run.bat
- LICENSE
