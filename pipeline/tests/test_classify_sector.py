"""Prueba la lógica de validación de classify_sector.py simulando la
respuesta de la API de Claude, sin llamar a Anthropic de verdad."""
import pytest

from pipeline.common import config
from pipeline.cv_classifier import classify_sector


class _FakeBlock:
    def __init__(self, type_, input_):
        self.type = type_
        self.input = input_


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, response):
        self._response = response

    def create(self, **kwargs):
        return self._response


class _FakeClient:
    def __init__(self, response):
        self.messages = _FakeMessages(response)


def _patch_anthropic(monkeypatch, response):
    monkeypatch.setattr(config, "anthropic_api_key", lambda: "test-key")
    monkeypatch.setattr(classify_sector.anthropic, "Anthropic", lambda api_key: _FakeClient(response))


def test_classify_cv_text_returns_valid_classification(monkeypatch):
    response = _FakeResponse(
        [
            _FakeBlock(
                "tool_use",
                {
                    "sector_code": "31-33",
                    "confidence": 0.9,
                    "rationale": "Operador de producción en planta automotriz.",
                },
            )
        ]
    )
    _patch_anthropic(monkeypatch, response)

    result = classify_sector.classify_cv_text("CV de ejemplo")

    assert result["sector_code"] == "31-33"
    assert result["confidence"] == 0.9
    assert result["alternative_sectors"] == []


def test_classify_cv_text_rejects_sector_code_outside_catalog(monkeypatch):
    response = _FakeResponse(
        [_FakeBlock("tool_use", {"sector_code": "99-99", "confidence": 0.5, "rationale": "inventado"})]
    )
    _patch_anthropic(monkeypatch, response)

    with pytest.raises(classify_sector.InvalidClassification):
        classify_sector.classify_cv_text("CV de ejemplo")


def test_classify_cv_text_raises_when_no_tool_use_block(monkeypatch):
    response = _FakeResponse([_FakeBlock("text", None)])
    _patch_anthropic(monkeypatch, response)

    with pytest.raises(classify_sector.InvalidClassification):
        classify_sector.classify_cv_text("CV de ejemplo")
