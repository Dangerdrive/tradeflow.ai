"""Testes do extrator (LLM + fallback) — LLM mockado, sem rede, <1s."""

from extraction.extractor import InvoiceExtractor
from extraction.schemas import InvoiceData
from tests.fixtures.sample_pdf import INVOICE_EN, make_pdf
from utils.llm import LlmClient


class _Resposta:
    def __init__(self, content: str) -> None:
        self.content = content


class _ChatLlmSucesso:
    """Devolve sempre JSON válido de InvoiceData."""

    def __init__(self, **kwargs) -> None:
        self.chamadas = 0

    def invoke(self, prompt: str) -> _Resposta:
        self.chamadas += 1
        return _Resposta(
            '{"numero_fatura": "INV-2026-0842", "fornecedor": "Tech Global Ltd.", '
            '"valor_total_usd": 12850.40, "peso_bruto_kg": 320.5, '
            '"incoterm": "FOB", "volumes": 12, "moeda": "USD", '
            '"itens": [{"ncm": "8528.72.00", "descricao": "Televisor LED 55", '
            '"quantidade": 10, "valor": 12850.40}]}'
        )


class _ChatLlmFalha:
    """Levanta erro — força o fallback por regex."""

    def __init__(self, **kwargs) -> None:
        pass

    def invoke(self, prompt: str) -> _Resposta:
        raise ConnectionError("serviço indisponível")


class _ChatLlmJsonInvalido:
    """Devolve texto que não é JSON — força fallback."""

    def __init__(self, **kwargs) -> None:
        pass

    def invoke(self, prompt: str) -> _Resposta:
        return _Resposta("Não entendi o documento.")


def _extrator(chat) -> InvoiceExtractor:
    llm = LlmClient(api_key="sk-test", chat_cls=lambda **_: chat)
    return InvoiceExtractor(llm)


def test_extrai_de_texto_com_llm() -> None:
    chat = _ChatLlmSucesso()
    dados = _extrator(chat).extract_from_text("COMMERCIAL INVOICE\nInvoice No.: INV-2026-0842")
    assert isinstance(dados, InvoiceData)
    assert dados.numero_fatura == "INV-2026-0842"
    assert dados.incoterm.value == "FOB"
    assert dados.itens[0].ncm == "8528.72.00"


def test_extrai_de_pdf_com_llm(tmp_path) -> None:
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(make_pdf(INVOICE_EN))
    dados = _extrator(_ChatLlmSucesso()).extract_from_pdf(pdf)
    assert dados.fornecedor == "Tech Global Ltd."


def test_llm_falha_usa_fallback_regex() -> None:
    dados = _extrator(_ChatLlmFalha()).extract_from_text("\n".join(INVOICE_EN))
    # O fallback regex extrai o número da fatura do texto.
    assert dados.numero_fatura == "INV-2026-0842"


def test_llm_json_invalido_usa_fallback() -> None:
    dados = _extrator(_ChatLlmJsonInvalido()).extract_from_text(
        "COMMERCIAL INVOICE\nInvoice No.: INV-777\nSupplier: Beta"
    )
    assert dados.numero_fatura == "INV-777"
    assert dados.fornecedor == "Beta"


def test_extrator_nunca_levanta_excecao_sem_controle() -> None:
    dados = _extrator(_ChatLlmFalha()).extract_from_text("")
    assert isinstance(dados, InvoiceData)
