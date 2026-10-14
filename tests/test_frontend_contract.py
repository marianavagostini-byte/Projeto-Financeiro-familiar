import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "frontend" / "index.html"


class ElementIdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for name, value in attrs if name == "id")


def test_ids_html_sao_unicos_e_referencias_javascript_existentes():
    html = FRONTEND.read_text(encoding="utf-8")
    parser = ElementIdParser()
    parser.feed(html)
    contagens = Counter(parser.ids)
    duplicados = sorted(elemento_id for elemento_id, total in contagens.items() if total > 1)
    referencias = set(re.findall(r'getElementById\("([^"]+)"\)', html))

    assert duplicados == []
    assert referencias.issubset(set(parser.ids))


def test_frontend_configura_api_e_usa_rotas_documentadas():
    html = FRONTEND.read_text(encoding="utf-8")
    assert 'name="api-base-url"' in html
    assert '"/usuarios/"' in html
    assert '"/token"' in html
    assert '"/transacoes/"' in html
    assert '`/transacoes/resumo-membros${query}`' in html
