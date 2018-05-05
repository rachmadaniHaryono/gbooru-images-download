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
