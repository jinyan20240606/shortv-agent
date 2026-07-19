# coding=utf-8
import re

import requests


URL_RE = re.compile(r"https?://[^\s，。)）]+")


def extract_first_url(text):
    match = URL_RE.search(text or "")
    return match.group(0).rstrip(".,，。") if match else text


def normalize_douyin_url(text, timeout=15):
    url = extract_first_url(text)
    if not url:
        return text
    if "v.douyin.com" not in url:
        return url

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        allow_redirects=True,
        timeout=timeout,
    )
    return response.url
