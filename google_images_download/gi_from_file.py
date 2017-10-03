#!/usr/bin/env python3
"""google image related function.

modified version from
http://stackoverflow.com/a/28792943
"""
import json
import webbrowser
from pprint import pprint

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def get_default_session():
    ua = UserAgent()
    session = requests.Session()
    session.headers.update({'User-Agent':ua.firefox})
    return session


def get_post_response(file_path, session=None, return_mode='response'):
    """Get post response."""
    session = session if session is not None else get_default_session()
    search_url = 'http://www.google.com/searchbyimage/upload'
    multipart = {'encoded_image': (file_path, open(file_path, 'rb')), 'image_content': ''}
    response = session.post(search_url, files=multipart, allow_redirects=False)
    if return_mode == 'url':
        return response.heaers['Location']
    else:
        return response


def get_first_page_data(file_path, session=None):
    """Get first page data from location url."""
    session = session if session is not None else get_default_session()
    post_resp = get_post_response(file_path, session)
    resp = session.get(post_resp.headers['Location'])
    soup = BeautifulSoup(resp.text, 'html.parser')
    res = {}
    # link to other size
    for a_tag in soup.select('._v6 span.gl a'):
        res.setdefault('other_size', {}).update(
            {a_tag.text: a_tag.attrs.get('href', None)})
    # best guess
    bg_tag = soup.select('div.card-section a')[-1]
    res['best_guess'] = {bg_tag.text: bg_tag.attrs.get('href', None)}
    # page results
    for h_tag in soup.select('.g'):
        pr_item = {}
        pr_item['title'] =  h_tag.select_one('h3 a').text
        pr_item['url'] =  h_tag.select_one('h3 a').attrs.get('href', None)
        pr_item['data'] = h_tag.select_one('span.st .f')
        pr_item['data'] = pr_item['data'].text if pr_item['data'] else None
        pr_item['text'] = h_tag.select_one('span.st')
        if pr_item['text']:
            pr_item['text'] = h_tag.select_one('span.st').text
        if pr_item['data'] and pr_item['text']:
            pr_item['text'] = h_tag.select_one('span.st').text.replace(pr_item['data'], '', 1)
        res.setdefault('page_results', []).append(pr_item)
    # visually similar link
    res['visually_similar_image_link'] = \
        soup.select_one('.iu-card-header').attrs.get('href', None)
    # visually_similar_image_item
    for h_tag in soup.select('.img-brk .rg_ul .uh_r'):
        vs_item = {}
        vs_item['link'] = h_tag.select_one('a').attrs.get('href', None)
        vs_item['img_src'] = h_tag.select_one('img').attrs.get('src', None)
        vs_item['img_title'] = h_tag.select_one('img').attrs.get('title', None)
        vs_item['json_data'] = json.loads(h_tag.select_one('.rg_meta').text)
        res.setdefault('visually_similar_image_item', []).append(vs_item)
    # pages with matching image
    for h_tag in soup.select('.srg .g'):
        pmi_item = {}
        pmi_item['link'] = h_tag.select_one('a').attrs.get('href', None)
        pmi_item['title'] = h_tag.select_one('a').text
        pmi_item['text_data'] = h_tag.select_one('span.st .f').text
        pmi_item['text'] = h_tag.select_one('span.st').text
        pmi_item['text'] = pmi_item['text'].replace(pmi_item['text_data'], '', 1)
        pmi_item['img_src'] = h_tag.select_one('img').attrs.get('src', None)
        res.setdefault('pages_with_matching_image', []).append(vs_item)
    # pages link
    for h_tag in soup.select('table#nav a'):
        res.setdefault('pages_link', {}).update({
            h_tag.text: h_tag.attrs.get('href', None)})
    return res


def search(file_path, mode='browser'):
    """Run simple program that search image."""
    session = get_default_session()
    if mode == 'data':
        res = first_page_data(file_path, session)
        pprint(res)
    else:
        fetch_url = get_post_response(file_path, session, 'url')
        webbrowser.open(fetch_url)
