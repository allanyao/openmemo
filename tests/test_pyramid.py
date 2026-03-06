import pytest
import time
from openmemo.pyramid.pyramid_engine import PyramidEngine
from openmemo.pyramid.summarizer import Summarizer


class TestSummarizer:
    def test_single_cell(self):
        s = Summarizer()
        result = s.summarize([{"content": "hello world"}])
        assert result == "hello world"

    def test_multiple_cells(self):
        s = Summarizer()
        result = s.summarize([
            {"content": "fact one"},
            {"content": "fact two"},
        ])
        assert "fact one" in result
        assert "fact two" in result

    def test_empty(self):
        s = Summarizer()
        assert s.summarize([]) == ""

    def test_max_length(self):
        s = Summarizer()
        result = s.summarize([{"content": "x" * 500}], max_length=100)
        assert len(result) <= 100


class TestPyramidEngine:
    def test_process_recent_cells(self):
        engine = PyramidEngine(summarizer=Summarizer())
        cells = [
            {"id": f"c{i}", "content": f"cell {i}", "created_at": time.time()}
            for i in range(10)
        ]
        result = engine.process(cells)
        assert result["short_term"] == 10
        assert result["promotions"] == 0

    def test_process_old_cells(self):
        engine = PyramidEngine(summarizer=Summarizer())
        old_time = time.time() - 86400 * 2
        cells = [
            {"id": f"c{i}", "content": f"cell {i}", "created_at": old_time}
            for i in range(10)
        ]
        result = engine.process(cells)
        assert result["mid_term"] == 10
