from tender_agents.research.fetchers import detect_captcha


def test_detect_captcha_showcaptcha():
    html = "<html><body><div id='showcaptcha'>...</div></body></html>"
    assert detect_captcha(html) is True


def test_detect_captcha_checkbox():
    assert detect_captcha("<div class='checkbox-captcha'>") is True


def test_detect_captcha_clean_page():
    assert detect_captcha("<html><body><h1>Контакты</h1><p>email@test.ru</p></body></html>") is False
