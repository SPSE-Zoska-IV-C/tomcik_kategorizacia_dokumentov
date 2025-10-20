from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import os

MODEL_PATH = os.path.join("ai", "model")  # musí obsahovať config + pytorch_model.bin + tokenizer

# načítanie pipeline raz pri spustení aplikácie
def load_classifier():
    if not os.path.isdir(MODEL_PATH):
        raise FileNotFoundError("Model nebol nájdený v ai/model. Najprv ho natrénuj a daj sem.")
    classifier = pipeline("text-classification", model=MODEL_PATH, tokenizer=MODEL_PATH, truncation=True)
    return classifier

# vytvor globálny objekt
CLASSIFIER = None

def init():
    global CLASSIFIER
    if CLASSIFIER is None:
        CLASSIFIER = load_classifier()

def analyze_text(text):
    """
    Vráti label (reťazec), napr. 'financne'
    """
    if CLASSIFIER is None:
        init()
    # pipeline vráti list dictov, berieme prvý
    out = CLASSIFIER(text[:4000])  # obmedz na primeranú dĺžku, ak treba
    return out[0]["label"]
