"""Test for models module."""
from urllib.parse import urlparse, parse_qs
import os

from PIL import Image
import pytest
import vcr

from gbooru_images_download import models


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
        'image_guess': 'check for dead pixels',
        'search_url':
            'http://www.google.com/search?'
            'tbs=sbi:AMhZZivJeVMaIy-Czt346tQLdTKhmNlzyMCacQBuRdR3KsVoGDZl7bwKFXeTOX8aRP8_1rrffzyqe'
            'vAHM-ZLF66B4dawe_1IgVqNQgJokBnCO8-hSrXOLBJfT1dCB4uTj1A3wa-z8qKvyhRVN2txG_1BtlXYUmtHOF'
            'z8Te9iHANJk-_1f44BXXWI9Zbq9Yd-JOgXPmaIjzT6FHT4UFGJ2S69P1ixik_1pTLhXQp0Yp0V2aGhs396O93'
            'tCrTnkIpqroTlyVHd5h_1iX6FfD0Vcw60Z9DLnPXOFLAyLmB-HILSFgYxH72V5GjCxDDv4GGwhG-8tV6n4dmk'
            'CgGVhs',
        'similar_search_url':
            'https://www.google.com/search?'
            'tbs=simg:CAEShgIJAGUUt_1bm7g0a-gELEKjU2AQaBAgVCAgMCxCwjKcIGl8KXQgDEiVH_1wi0As8B_1ggos'
            'gLyAvgIKaArsyqIJ9conTehK4QjnjesNtMnGjDr2WYL3JwKke7gjGUtkou0VlOLR40JczbbhOx4-RDy03I_1k'
            'UV6WgCRiPqIUovom1AgBAwLEI6u_1ggaCgoICAESBM9Xj5QMCxCd7cEJGmkKGAoGb3Jhbmdl2qWI9gMKCggvb'
            'S8wamNfcAoYCgVwZWFjaNqliPYDCwoJL20vMDNyMTh5ChkKB3BhdHRlcm7apYj2AwoKCC9tLzBod2t5ChgKBW'
            'FtYmVy2qWI9gMLCgkvbS8wNGQwMWYM&'
            'q=check+for+dead+pixels&tbm=isch&sa=X&ved=0ahUKEwi3o6zp3IrXAhUJahoKHfAKCekQsw4INQ',
        'size_search_url':
            'https://www.google.com/search?'
            'q=check+for+dead+pixels&'
            'tbm=isch&tbs=simg:CAQSlAEJAGUUt_1bm7g0aiAELEKjU2AQaBAgVCAgMCxCwjKcIGl8KXQgDEiVH_1wi0A'
            's8B_1ggosgLyAvgIKaArsyqIJ9conTehK4QjnjesNtMnGjDr2WYL3JwKke7gjGUtkou0VlOLR40JczbbhOx4-'
            'RDy03I_1kUV6WgCRiPqIUovom1AgBAwLEI6u_1ggaCgoICAESBM9Xj5QM&sa=X&'
            'ved=0ahUKEwi3o6zp3IrXAhUJahoKHfAKCekQ2A4IIygB'}
