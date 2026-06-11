from tender_agents.browser.text_blocks import (
    parse_tender_detail_text,
    split_listing_blocks,
    extract_procedure_number,
)


def test_parse_tender_detail_text():
    text = """
    Сведения о закупке № 0372000000326000052
    Наименование объекта закупки:
    Поставка аппарата для сварки
    Начальная (максимальная) цена контракта / Максимальное значение цены контракта:
    3 863.00
    Сведения об организаторе торгов:
    Тестовый Заказчик
    Дата и время окончания срока подачи заявок:
    01.06.2024 18:00:00
    Контактная информация:
    Иванов Иван, +79991234567
    24.05.2024 10:00:00 Публикация извещения
    """
    fields = parse_tender_detail_text(text)
    assert fields["external_id"] == "0372000000326000052"
    assert fields["title"] == "Поставка аппарата для сварки"
    assert fields["price"] == "3 863.00"
    assert fields["customer_name"] == "Тестовый Заказчик"
    assert fields["deadline_str"] == "01.06.2024 18:00:00"
    assert fields["contacts"] == "Иванов Иван, +79991234567"
    assert fields["publish_date_str"] == "24.05.2024"


def test_split_listing_blocks():
    text = """
    Найдено процедур 2
    № 111
    Поставка молока
    1000 RUB
    № 222
    CRM система
    2000 RUB
    """
    blocks = split_listing_blocks(text)
    assert len(blocks) == 2
    assert extract_procedure_number(blocks[0]) == "111"
    assert "молока" in blocks[0]
    assert extract_procedure_number(blocks[1]) == "222"
