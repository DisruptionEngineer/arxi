from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class OCRResult:
    text: str
    confidence: float
    raw_blocks: list[dict] = field(default_factory=list)
    REVIEW_THRESHOLD: ClassVar[float] = 0.7

    @property
    def needs_review(self) -> bool:
        return self.confidence < self.REVIEW_THRESHOLD


class OCREngine:
    def __init__(self):
        try:
            import pytesseract

            self._tesseract = pytesseract
        except ImportError:
            self._tesseract = None

    def extract(self, image_path: str) -> OCRResult:
        if self._tesseract is None:
            raise RuntimeError("Tesseract not available")
        from PIL import Image

        img = Image.open(image_path)
        data = self._tesseract.image_to_data(
            img, output_type=self._tesseract.Output.DICT
        )
        texts = []
        confidences = []
        blocks = []
        for i, text in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 0 and text.strip():
                texts.append(text)
                confidences.append(conf)
                blocks.append(
                    {
                        "text": text,
                        "confidence": conf,
                        "x": data["left"][i],
                        "y": data["top"][i],
                    }
                )
        avg_conf = (
            sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
        )
        return OCRResult(
            text=" ".join(texts), confidence=avg_conf, raw_blocks=blocks
        )
