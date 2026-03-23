# ai/predict.py
from transformers import pipeline
from functools import lru_cache
import torch

# Viacjazyčný NLI model vhodný pre zero-shot klasifikáciu (funguje dobre aj so slovenčinou)
MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

# Cieľové štítky, ktoré používame v appke
CANDIDATE_LABELS = ["pravne", "financne", "osobne", "clanky", "spravy"]
DEFAULT_LABEL = "nezaradene"
MIN_CONFIDENCE = 0.45  # Ak je istota nižšia, zaradíme medzi nezaradené


@lru_cache(maxsize=1)
def _get_classifier():
    """
    Lazy inicializácia zero-shot pipeline, aby sa nahrala len raz.
    """
    device = 0 if torch.cuda.is_available() else -1
    return pipeline(
        "zero-shot-classification",
        model=MODEL_NAME,
        device=device,
        truncation=True
    )


def predict_category(text: str, candidate_labels=None):
    """Predikcia kategórie pre text.

    - text: obsah dokumentu
    - candidate_labels: zoznam názvov kategórií (v slovenčine), napr.
      ["pravne", "financne", "clanky", "spravy", "osobne"]
    Vráti (label, confidence_percent).
    """
    if not text or not text.strip():
        return DEFAULT_LABEL, 0.0

    labels = candidate_labels or CANDIDATE_LABELS
    # musia byť aspoň 2, inak nemá zmysel volanie modelu
    if not labels or len(labels) < 2:
        return DEFAULT_LABEL, 0.0

    # Orezanie extrémne dlhých textov pre stabilnejšie spracovanie
    snippet = text[:4000]

    classifier = _get_classifier()
    result = classifier(
        snippet,
        candidate_labels=labels,
        # slovensky formulovaná hypotéza pomáha modelu pri rozhodovaní
        hypothesis_template="Tento dokument patrí do kategórie {}."
    )

    if not result or "labels" not in result or not result["labels"]:
        return DEFAULT_LABEL, 0.0

    label = result["labels"][0]
    score = float(result["scores"][0]) if result["scores"] else 0.0

    if score < MIN_CONFIDENCE:
        return DEFAULT_LABEL, round(score * 100, 2)

    return label.lower(), round(score * 100, 2)


if __name__ == "__main__":
    samples = [
        "Faktúra č. 1023 za servis IT pre TechnoSoft s.r.o.; suma 420 EUR, splatnosť 12.10.2024.",
        "Zmluva o prenájme bytu medzi dvoma osobami uzavretá dňa 01.09.2023.",
        "Denníkový záznam: dnes som riešil tréning, potom nákup a plánujem výlet do Tatier.",
        "Článok: Analýza umelej inteligencie a dopad na zdravotníctvo v roku 2025.",
        "Krátke správy: Bratislava – dopravná nehoda na D1, kolóny 45 minút."
    ]
    for s in samples:
        print(s, "=>", predict_category(s))
