from pathlib import Path
from collections import Counter
import math
import re

import spacy
from spacy.cli import download

BASE_DIR = Path(__file__).resolve().parent
TFIDF_DIR = BASE_DIR / '../task4/tfidf_outputs/lemmas'
URL_FILE = BASE_DIR / '../task1/urls.txt'
RESULTS_COUNT = 10


# download("en_core_web_sm")  # скачиваем модель, если она не установлена


def load_doc_vectors():
    doc_vectors = {}
    doc_norms = {}
    lemma_idf = {}

    for path in sorted(TFIDF_DIR.glob('*_lemmas_tfidf.txt'),
                       key=lambda current_path: int(current_path.stem.split('_')[0])):
        doc_id = int(path.stem.split('_')[0])
        vector = {}
        norm_square = 0.0

        with path.open('r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 3:
                    continue

                lemma = parts[0]
                idf = float(parts[1])
                tfidf = float(parts[2])

                vector[lemma] = tfidf
                norm_square += tfidf * tfidf

                if lemma not in lemma_idf:
                    lemma_idf[lemma] = idf

        doc_vectors[doc_id] = vector
        doc_norms[doc_id] = math.sqrt(norm_square)

    return doc_vectors, doc_norms, lemma_idf


# загружаем doc_id -> url
def load_doc_urls():
    doc_urls = {}

    with URL_FILE.open('r', encoding='utf-8') as f:
        for doc_id, line in enumerate(f, start=1):
            doc_urls[doc_id] = line.strip()

    return doc_urls


def build_query_vector(query, nlp, lemma_idf):
    # обрабатываем запрос
    query = query.replace("’", "'").replace("‘", "'")  # нормализуем апострофы
    query = query.lower()
    query = re.sub(r"[^a-zA-Z'\s]", " ", query)
    query = re.sub(r"\s+", " ", query).strip()

    doc = nlp(query)
    query_counts = Counter()

    for token in doc:
        if token.is_stop or token.is_space or token.tag_ == "POS" or token.text in ("'", ""):
            continue

        lemma = token.lemma_.strip()
        if lemma and lemma in lemma_idf:
            query_counts[lemma] += 1

    # собираем вектор запроса
    query_vector = {}
    for lemma, tf in query_counts.items():
        query_vector[lemma] = tf * lemma_idf[lemma]

    return query_vector


# косинусное расстояние
def cosine_similarity(query_vector, doc_vector, query_norm, doc_norm):
    if query_norm == 0 or doc_norm == 0:
        return 0.0

    dot_product = 0.0
    for lemma, query_weight in query_vector.items():
        dot_product += query_weight * doc_vector.get(lemma, 0.0)

    if dot_product == 0:
        return 0.0

    return dot_product / (query_norm * doc_norm)


def search(query_vector, doc_vectors, doc_norms):
    query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
    ranked_docs = []

    # для каждого документа считаем косинусное расстояние с запросом
    for doc_id, doc_vector in doc_vectors.items():
        similarity = cosine_similarity(query_vector, doc_vector, query_norm, doc_norms[doc_id])
        if similarity == 0:
            continue

        distance = 1.0 - similarity
        ranked_docs.append((distance, doc_id))

    ranked_docs.sort()
    return ranked_docs[:RESULTS_COUNT]


print("Loading TF-IDF vectors...")
doc_vectors, doc_norms, lemma_idf = load_doc_vectors()
print("TF-IDF vectors loaded.")

print("Loading URLs...")
doc_urls = load_doc_urls()
print("URLs loaded.")

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_sm")
print("Model loaded.\n")

while True:
    query = input("Query (type 'exit' to quit): ").strip()

    if query == "exit" or query == "":
        print("Session finished.")
        break

    query_vector = build_query_vector(query, nlp, lemma_idf)
    top_docs = search(query_vector, doc_vectors, doc_norms)

    print("Doc IDs:", [doc_id for _, doc_id in top_docs])
    print("URLs:")
    for _, doc_id in top_docs:
        print(doc_urls[doc_id])

    print()
