# ai/predict.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# --- Konštanty / mapovania ---
MODEL_PATH = "ai/model"
ID2LABEL = {0: "pravne", 1: "financne", 2: "osobne", 3: "clanky", 4: "spravy"}

# Max. dĺžka jedného okna (musí sedieť s tréningom); stride dáva prekrytie medzi oknami
MAX_LEN = 256
STRIDE = 64
THRESHOLD = 0.60  # 60 % – uprav podľa potrieb projektu

# --- Načítanie modelu/jednorazovo pri importe (Flask bude zdieľať tento proces) ---
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# bezpečne nastav pad token, ak by chýbal (niektoré checkpointy)
if tokenizer.pad_token_id is None:
    if tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    else:
        tokenizer.add_special_tokens({'pad_token': '[PAD]'})
        model.resize_token_embeddings(len(tokenizer))

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()


@torch.no_grad()
def _predict_chunks(input_ids: torch.Tensor, attention_mask: torch.Tensor):
    """
    Vypočíta logity pre batch chunkov a vráti ich priemer.
    input_ids/attention_mask: tvar [num_chunks, seq_len]
    """
    # presun na device
    input_ids = input_ids.to(device)
    attention_mask = attention_mask.to(device)

    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    # tvar: [num_chunks, num_labels]
    logits = outputs.logits
    # agregácia cez chunky – priemer (môžeš skúsiť aj max)
    return logits.mean(dim=0)


@torch.no_grad()
def predict_category(text: str):
    """
    Predikcia kategórie pre ľubovoľne dlhý text.
    Používa sliding-window cez tokenizer(return_overflowing_tokens=True).
    Vráti (label, confidence_percent).
    Pri nízkej istote (< THRESHOLD) vráti ('nezaradene', conf%).
    """

    if not text or not text.strip():
        return "nezaradene", 0.0

    # Pre dlhé texty použijeme oficiálny overflow režim (sliding-window)
    enc = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LEN,
        stride=STRIDE,
        return_overflowing_tokens=True,
        padding="max_length"
    )

    input_ids = enc["input_ids"]
    attention_mask = enc["attention_mask"]

    # Pri viacerých overflow-och budeme mať viac riadkov (chunkov)
    # Agregujeme logity cez všetky chunk-y
    logits = _predict_chunks(input_ids, attention_mask)
    probs = torch.softmax(logits, dim=-1)

    conf, idx = torch.max(probs, dim=-1)
    label = ID2LABEL[idx.item()]
    confidence = conf.item()

    if confidence < THRESHOLD:
        return "nezaradene", round(confidence * 100, 2)

    return label, round(confidence * 100, 2)


# --- Voliteľné: rýchly manuálny test (spustiť len keď súbor spúšťaš priamo) ---
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
