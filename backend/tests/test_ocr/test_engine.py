from arxi.ocr.engine import OCREngine, OCRResult


def test_ocr_result_structure():
    """Test OCR result dataclass has expected fields."""
    result = OCRResult(text="Take 1 tablet daily", confidence=0.92, raw_blocks=[])
    assert result.text == "Take 1 tablet daily"
    assert result.confidence == 0.92
    assert result.needs_review is False


def test_ocr_low_confidence_flags_review():
    result = OCRResult(text="T4ke 1 t@blet da1ly", confidence=0.45, raw_blocks=[])
    assert result.needs_review is True
