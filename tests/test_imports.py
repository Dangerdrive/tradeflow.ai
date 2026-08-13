"""Testes de importação/versão — comprovam que o upgrade da Fase U2 aplicou.

Para cada dependência, afirma que a versão instalada é >= um limite mínimo
maior que o baseline pré-upgrade. (O `pypdf` é a exceção: <6 por restrição do
crewai->embedchain, resolvido na Fase U3.)
"""

import importlib
import importlib.metadata as md


def _ver(tuple_str: str) -> tuple[int, ...]:
    """Converte 'a.b.c' em tupla de ints para comparação segura."""
    parts = []
    for p in tuple_str.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


MINIMOS: dict[str, tuple[int, ...]] = {
    "pydantic": (2, 10),
    "pydantic-settings": (2, 10),
    "sqlalchemy": (2, 0, 40),
    "fastapi": (0, 120),
    "streamlit": (1, 50),
    "pandas": (2, 3),
    "scikit-learn": (1, 6),
    "pdfplumber": (0, 11, 5),
    "pypdf": (4, 0),  # <6 até a Fase U3 (crewai/embedchain)
    "python-multipart": (0, 0, 15),
    "python-dotenv": (1, 1),
    "alembic": (1, 14),
    "joblib": (1, 5),
    "pillow": (12, 0),
    "starlette": (0, 40),
    "uvicorn": (0, 32),
}


def test_versoes_minimas_da_fase_u2() -> None:
    erros: list[str] = []
    for pkg, minimo in MINIMOS.items():
        instalado = _ver(md.version(pkg))
        if instalado < minimo:
            erros.append(f"{pkg}: {'.'.join(map(str, instalado))} < {'.'.join(map(str, minimo))}")
    assert not erros, "Dependências abaixo do mínimo da Fase U2:\n" + "\n".join(erros)


def test_pypdf_esta_instalado_e_importa() -> None:
    import pypdf

    assert hasattr(pypdf, "PdfWriter")
    assert hasattr(pypdf, "PdfReader")


def test_pypdf2_removido() -> None:
    # PyPDF2 foi substituído por pypdf
    import importlib.util

    assert importlib.util.find_spec("PyPDF2") is None


def test_importacao_dos_modulos() -> None:
    modulos = [
        "pdfplumber",
        "sqlalchemy",
        "fastapi",
        "streamlit",
        "pandas",
        "sklearn",
        "pydantic_settings",
        "alembic",
        "slowapi",
        "starlette",
    ]
    for mod in modulos:
        assert importlib.import_module(mod) is not None, f"falhou import: {mod}"
