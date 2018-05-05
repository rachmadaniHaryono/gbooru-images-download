"""Test for api module."""
import logging
import json

from bs4 import BeautifulSoup
from PIL import Image
import pytest
import requests
import vcr

from gbooru_images_download import api, models

logging.basicConfig()
vcr_log = logging.getLogger("vcr")
vcr_log.setLevel(logging.INFO)


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
@vcr.use_cassette('cassette/test_get_or_create_search_query.yaml', record_mode='new_episodes')
def test_get_or_create_search_query(tmp_db):
    """test method."""
    res = api.get_or_create_search_query('red picture')[0]
    tmp_db.session.add(res)
    tmp_db.session.commit()
    json_items = []
    non_json_items = []
    logging.debug('created at {}'.format(res.created_at))
    res_vars = vars(res)
    for key, value in res_vars.items():
        try:
            json.dumps(value)
            json_items.append((key, value))
        except TypeError:
            non_json_items.append((key, value))
    assert set(json_items) == set(
        [('page', 1), ('search_term_id', 1), ('id', 1)])
    assert list(zip(*non_json_items))[0] == ('_sa_instance_state', 'created_at')
    assert res
    assert len(res.match_results) > 0


@pytest.mark.no_travis
@vcr.use_cassette('cassette/test_get_or_create_search_query_duplicate.yaml', record_mode='new_episodes')  # NOQA
def test_get_or_create_search_query_duplicate(tmp_db):
    """test method."""
    v1 = api.get_or_create_search_query('red picture', disable_cache=True)[0]
    v2 = api.get_or_create_search_query('red picture', disable_cache=True)[0]
    tmp_db.session.add_all([v1, v2])
    tmp_db.session.commit()
    assert models.MatchResult.query.count() == 100


@pytest.mark.no_travis
@vcr.use_cassette('cassette/test_get_or_create_match_result_from_json_resp.yaml', record_mode='new_episodes')  # NOQA
def test_get_or_create_match_result_from_json_resp(tmp_db):
    """test method."""
    query_url = \
        'https://www.google.com/search' \
        '?q=red+picture&tbm=isch&ijn=0&start=0&asearch=ichunk&async=_id%3Arg_s%2C_pms%3As'
    resp = requests.get(query_url)
    json_resp = resp.json()
    res = api.get_or_create_match_result_from_json_resp(json_resp)
    m1 = next(res)
    assert m1[1]
    assert m1[0].img_url
    tmp_db.session.add(m1[0])
    tmp_db.session.commit()
    assert m1[0].img_url
    m_list = [m1[0]]
    m_list.extend([x[0] for x in res])
    assert all([x.img_url for x in m_list])


@pytest.mark.no_travis
def test_add_tags_to_image_url(tmp_db):
    """test method."""
    args = {
        'img_url': {'url': 'http://example.com/1.jpg', 'width': 2560, 'height': 1920},
        'img_url_tags': [
            {'name': 'picture title', 'namespace': 'picture title'},
            {'name': 'site', 'namespace': 'site'},
            {'name': 'site', 'namespace': 'site'},
            {'name': 'img', 'namespace': 'img ext'}],
    }
    img_url, _ = models.get_or_create(
        tmp_db.session, models.ImageURL, **args['img_url'])
    img_url_tags = api.add_tags_to_image_url(img_url, args['img_url_tags'])
    models.db.session.add_all([img_url] + img_url_tags)
    models.db.session.commit()
    assert len(img_url.tags) > 0


@pytest.mark.no_travis
@vcr.use_cassette('cassette/test_get_or_create_search_image.yaml', record_mode='new_episodes')  # NOQA
def test_get_or_create_search_image(tmp_pic, tmp_db, tmpdir):
    """test method."""
    res, created = api.get_or_create_search_image(
        tmp_pic['image_input'].strpath, thumb_folder=tmpdir.strpath)
    assert created
    assert len(res.text_matches) > 2
    assert len(res.main_similar_results) > 2


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
