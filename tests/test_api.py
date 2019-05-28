"""Test for api module."""
from bs4 import BeautifulSoup
from PIL import Image
import pytest
import requests
import vcr

from gbooru_images_download import api, models


@pytest.fixture()
def tmp_pic(tmpdir):
    """Temporary pic."""
    img_input = tmpdir.join("test.jpg")
    img = Image.new('RGB', (500, 500), 'red')
    img.save(img_input.strpath)
    return {
        'image_input': img_input,
        'image': img,
        'checksum': '0deee6f6b714650064a6b42b9b306e0a95f12b2e3df54d77c9b8eb2cae78e075',
        'thumb_checksum': '9e5ffe7f0af13b394210ff8991eb7d75ade95ba2124a084c9d21fa2234a49428',
        'image_size': (500, 500),
        'thumb_size': (250, 250),
    }


@pytest.mark.no_travis
@vcr.use_cassette('cassette/test_parse_img_search_html.yaml', record_mode='new_episodes')  # NOQA
def test_parse_img_search_html(tmp_db):
    search_url = \
        'https://www.google.com/search?' \
        'tbs=sbi:AMhZZiuRcL-7EZ68pSb2tia8TSx_1dBYpKWw59vDWJY4Ik6C2C1gfn3VPl86m-' \
        'nUcsgtuU7cW9MNs3Gf733_1Xjw16boD7WIKtd9ZidpgSDN00MRlFrecizNHZTvTGL0f5Bx-' \
        'tKxPLUqgy4qWd65iWU7EAQ4psAz6CPLJsfaXGrunvhj5FCIpLtMX3T3kKku2G-' \
        'KqnoKFV8kqGi324YeKV-' \
        'EshVR0mBp8Nfdy6kQwquFnGHrGSnjTERXz6djAh74BbupSVN36_' \
        '1WpcXk9dPBsac6iQxrdZZjE8ioj9xvNbM4vHYV2OZGyl6cfwUV9lWHnk4K9j5W_16_1sj4t' \
        '&safe=off'
    html_text = api.get_html_text(search_url=search_url)
    search_page = BeautifulSoup(html_text, 'lxml')
    data = api.parse_img_search_html(search_page)
    assert data['img_guess']
    assert data['similar_search_url']
    assert data['size_search_url']
    assert data['TextMatch']
    assert data['MainSimilarResult']
