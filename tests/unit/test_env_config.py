import types

import pytest

from backend.config import Settings
from backend.providers.fireworks import FireworksJudge


def test_settings_reads_env_vars(monkeypatch):
    # Ensure only the fallback variable is present for Mongo
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017/testdb")
    monkeypatch.setenv("FIREWORKS_API_KEY", "test-fireworks-key")

    s = Settings()
    assert s.mongo_uri.startswith("mongodb://")
    assert s.fireworks_api_key == "test-fireworks-key"


def test_fireworks_provider_available(monkeypatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "test-fireworks-key")
    s = Settings()
    judge = FireworksJudge(s)
    assert judge.available() is True


def test_mongo_client_not_instantiated_network(monkeypatch):
    # Verify we don't need a live connection to use Settings-derived values
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_CONNECTION_STRING", "mongodb://example:27017/db")
    s = Settings()
    # Just assert the config resolved without attempting any network call
    assert s.mongo_uri == "mongodb://example:27017/db"

