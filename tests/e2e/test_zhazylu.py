"""Сквозной тест (Playwright): клиент телефоннан жазылады. ФЕТ-14: 360 px экран.

Алдын ала стенд іске қосылған болуы керек (bash scripts/stand.sh start).
Іске қосу: pytest tests/e2e -q
"""
import os

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get('BASE', 'http://localhost:8000')


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={'width': 360, 'height': 740})
        yield pg
        browser.close()


def test_client_books_from_phone(page):
    page.goto(BASE + '/')
    page.locator('a.card').first.click()
    for i in range(1, 14):
        page.locator('.days a').nth(i).click()
        page.wait_for_load_state()
        if page.locator('input[name=start]').count():
            break
    page.locator('input[name=start]').first.check()
    page.fill('#id_client_name', 'Е2Е Тест')
    page.fill('#id_client_phone', '+77001112233')
    page.check('#id_consent')
    page.click('button[type=submit]')
    expect(page.locator('h1')).to_have_text('Сіз жазылдыңыз')


def test_no_consent_not_sent(page):
    page.goto(BASE + '/')
    page.locator('a.card').first.click()
    for i in range(1, 14):
        page.locator('.days a').nth(i).click()
        page.wait_for_load_state()
        if page.locator('input[name=start]').count():
            break
    page.locator('input[name=start]').first.check()
    page.fill('#id_client_name', 'Е2Е Тест')
    page.fill('#id_client_phone', '+77001112233')
    page.click('button[type=submit]')
    expect(page.locator('h1')).not_to_have_text('Сіз жазылдыңыз')
