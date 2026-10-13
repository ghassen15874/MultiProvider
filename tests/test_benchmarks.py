"""
Tests for Benchmarking Services
"""
import pytest
from app.services.benchmarking import BenchmarkingService

def test_extract_html_from_markdown():
    markdown_sample = """Here is your Pomodoro timer:
```html
<!DOCTYPE html>
<html>
<head><title>Timer</title></head>
<body><h1>Pomodoro</h1></body>
</html>
```
Enjoy your widget!"""

    extracted = BenchmarkingService.extract_html(markdown_sample)
    assert "<!DOCTYPE html>" in extracted
    assert "Enjoy your widget!" not in extracted
    assert extracted.startswith("<!DOCTYPE html>")
    assert extracted.endswith("</html>")

def test_extract_html_fallback():
    raw_html = "<div class='timer'>10:00</div>"
    extracted = BenchmarkingService.extract_html(raw_html)
    assert extracted == raw_html

def test_live_inference_chat():
    import asyncio
    from app.services.inference import InferenceService
    res = asyncio.run(InferenceService.chat_completion(
        model="allam-2-7b",
        messages=[{"role": "user", "content": "مرحبا"}],
        max_tokens=20
    ))
    assert "choices" in res
    assert len(res["choices"]) > 0
    assert "_rotator" in res
    assert res["_rotator"]["key_name"] is not None
