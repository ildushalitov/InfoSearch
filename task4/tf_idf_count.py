from pathlib import Path
from collections import Counter, defaultdict
import math

CLEANED_DIR = Path('../task1/cleaned')
LEMMA_DIR = Path('../task2/processed_txts')
OUT_TERMS_DIR = Path('./tfidf_outputs/terms')
OUT_LEMMAS_DIR = Path('./tfidf_outputs/lemmas')
OUT_TERMS_DIR.mkdir(parents=True, exist_ok=True)
OUT_LEMMAS_DIR.mkdir(parents=True, exist_ok=True)

DOC_START = 1
DOC_END = 200
doc_ids = [str(i) for i in range(DOC_START, DOC_END + 1)]
N = len(doc_ids)

# Загрузка глобального маппинга "лемма -> сет токенов"

global_lemma2tokens = defaultdict(set)
for doc_id in doc_ids:
    fn = LEMMA_DIR / f"{doc_id}_lemmas.txt"
    txt = fn.read_text(encoding='utf-8')
    for line in txt.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        lemma = parts[0]
        tokens = parts[1:]
        for t in tokens:
            global_lemma2tokens[lemma].add(t)

# множество всех токенов
tokens_in_mapping = set()
for toks in global_lemma2tokens.values():
    tokens_in_mapping.update(toks)

# Загрузка документов

doc_token_counts = {}  # doc_id -> Counter
for doc_id in doc_ids:
    raw = (CLEANED_DIR / f"{doc_id}.txt").read_text(encoding='utf-8')

    tokens = [t for t in raw.split() if t and (t in tokens_in_mapping)]
    doc_token_counts[doc_id] = Counter(tokens)

# DF для токенов

term_df = defaultdict(int)
for doc_id, cnt in doc_token_counts.items():
    for term in cnt.keys():
        term_df[term] += 1

# IDF для токенов

term_idf = {term: (math.log(N / df) + 1.0) for term, df in term_df.items()}

# TF для лемм -- сумма TF токенов

lemma_doc_tf = {doc_id: Counter() for doc_id in doc_ids}
for doc_id in doc_ids:
    token_counts = doc_token_counts[doc_id]
    for lemma, toks in global_lemma2tokens.items():
        tf_sum = 0
        for tok in toks:
            tf_sum += token_counts.get(tok, 0)
        if tf_sum > 0:
            lemma_doc_tf[doc_id][lemma] = tf_sum

# DF для лемм

lemma_df = defaultdict(int)
for lemma in global_lemma2tokens.keys():
    for doc_id in doc_ids:
        if lemma_doc_tf[doc_id].get(lemma, 0) > 0:
            lemma_df[lemma] += 1

# IDF для лемм

lemma_idf = {lemma: (math.log(N / df) + 1.0) for lemma, df in lemma_df.items() if df > 0}

# Запись токенов

for doc_id in doc_ids:
    cnt = doc_token_counts[doc_id]
    entries = []
    for term, tf in cnt.items():
        idf = term_idf.get(term, 0.0)
        tfidf = tf * idf
        entries.append((term, idf, tfidf))
    entries.sort(key=lambda x: x[2], reverse=True)
    out_path = OUT_TERMS_DIR / f"{doc_id}_terms_tfidf.txt"
    with out_path.open('w', encoding='utf-8') as f:
        for term, idf, tfidf in entries:
            f.write(f"{term} {idf:.6f} {tfidf:.6f}\n")

# Запись лемм

for doc_id in doc_ids:
    counter = lemma_doc_tf[doc_id]
    entries = []
    for lemma, tf in counter.items():
        idf = lemma_idf.get(lemma, 0.0)
        tfidf = tf * idf
        entries.append((lemma, idf, tfidf))
    entries.sort(key=lambda x: x[2], reverse=True)
    out_path = OUT_LEMMAS_DIR / f"{doc_id}_lemmas_tfidf.txt"
    with out_path.open('w', encoding='utf-8') as f:
        for lemma, idf, tfidf in entries:
            f.write(f"{lemma} {idf:.6f} {tfidf:.6f}\n")

print("Done")
