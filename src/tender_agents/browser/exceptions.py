class CaptchaRequiredError(Exception):
    """Исключение, выбрасываемое при обнаружении капчи или требования входа."""
    pass


class SiteUnreachableError(Exception):
    """Площадка не отвечает (таймаут, connection refused и т.п.)."""
    pass
