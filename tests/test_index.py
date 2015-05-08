from util import get_file

def test_index():
    """index page"""
    assert get_file('')

def test_favicon():
    """favicon"""
    assert get_file('favicon.ico')

def test_platform_icons():
    """platform icons"""
    assert get_file('platform/unknown.svg')
    assert get_file('platform/linux.svg')
    assert get_file('platform/darwin.svg')
    assert get_file('platform/windows.svg')
    assert get_file('platform/bsd.svg')
