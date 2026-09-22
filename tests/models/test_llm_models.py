"""Tests for src/models/llm_models.py."""

from src.models.llm_models import AvailableProcesses


class TestAvailableProcesses:
    """Tests for the AvailableProcesses enum."""

    def test_qualifier_value(self):
        assert AvailableProcesses.QUALIFIER.value == "qualifier"

    def test_classifier_value(self):
        assert AvailableProcesses.CLASSIFIER.value == "classifier"

    def test_two_members(self):
        assert len(AvailableProcesses) == 2

    def test_enum_iteration(self):
        values = [p.value for p in AvailableProcesses]
        assert "qualifier" in values
        assert "classifier" in values

    def test_lookup_by_name(self):
        assert AvailableProcesses["QUALIFIER"] == AvailableProcesses.QUALIFIER
        assert AvailableProcesses["CLASSIFIER"] == AvailableProcesses.CLASSIFIER

    def test_lookup_by_value(self):
        assert AvailableProcesses("qualifier") == AvailableProcesses.QUALIFIER
        assert AvailableProcesses("classifier") == AvailableProcesses.CLASSIFIER
