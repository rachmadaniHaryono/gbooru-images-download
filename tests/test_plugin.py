from yapsy.PluginManager import PluginManager

from gbooru_images_download import api, plugin


def test_main():
    manager = PluginManager(plugin_info_ext='ini')
    manager.setCategoriesFilter({
        "parser": api.ParserPlugin,
    })
    manager.setPluginPlaces([plugin.__path__[0]])
    manager.collectPlugins()
    assert manager.getAllPlugins()
    plugin_obj = manager.getPluginByName('Google image', 'parser')
    assert plugin_obj
    assert plugin_obj.name == 'Google image'
    assert not plugin_obj.is_activated
    assert manager.activatePluginByName('Google image', 'parser')
    assert plugin_obj.is_activated


def test_preprocessor():
    data = [
        (
            'imgres url', 'http://images.google.com/imgres?'
            'imgurl=http://cdn.hdporn4.me/javforme_img/42497/1-690x0.jpg&'
            'imgrefurl=http://javfor.me/42497.html&h=462&w=690&'
            'tbnid=58LnewbliqaN-M:&vet=1&docid=qipPGXAqJ5yzhM&'
            'ei=SLzxWs_tC4zovgTAqaTgDg&tbm=isch'),
        ('imgref url', 'http://<redacted>/42497.html'),
        ('cb', 21),
        ('cl', 21),
        ('cr', 18),
        ('id', '58LnewbliqaN-M:'),
        ('isu', '<redacted>'),
        ('ity', 'jpg'),
        ('msm', 'Ukuran lainnya'),
        (
            'msu', '/search?q=<redacted>&num=100&ie=UTF-8&tbm=isch&'
            'tbnid=58LnewbliqaN-M:&docid=qipPGXAqJ5yzhM'),
        ('pt', '<redacted>'),
        ('rh', '<redacted>'),
        ('rt', 0),
        ('s', ''),
        ('sc', 1),
        (
            'si', '/search?q=<redacted>&num=100&ie=UTF-8&tbm=isch&'
            'tbnid=58LnewbliqaN-M:&docid=qipPGXAqJ5yzhM'),
        ('sm', 'Mirip'),
        ('st', '<redacted>'),
        ('th', 184),
        ('tu', '<redacted>'),
        ('tw', 274)
    ]
    manager = api.get_plugin_manager()
    for plug in manager.getPluginsOfCategory('tag_preprocessor'):
        data = list(plug.plugin_object.run_tag_preprocessor(data))
