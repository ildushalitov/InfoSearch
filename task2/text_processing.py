import os
import glob
import re

from collections import defaultdict

import spacy  # библиотека дял токенизации и лемматизации
from spacy.cli import download

download("en_core_web_sm")  # скачиваем модель

nlp = spacy.load("en_core_web_sm")

input_dir = "../task1/cleaned"
output_dir = "processed_txts"
os.makedirs(output_dir, exist_ok=True)

pattern = os.path.join(input_dir, "*.txt")
for filepath in glob.glob(pattern):

    doc_id = os.path.splitext(os.path.basename(filepath))[0]

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("’", "'").replace("‘", "'")  # нормализуем апострофы

    # приведение к нижнему регистру и удаление нежелательных символов
    text = text.lower()
    text = re.sub(r"[^a-zA-Z'\s]", " ", text)
    text = re.sub(r'\s+', ' ', text).strip()

    doc = nlp(text)  # токенизация и лемматизация через spacy

    lemma_map = defaultdict(set)

    for token in doc:
        # пропускаем стоп-слова, пробелы, притяжательные маркеры и одиночные кавычки/пустые токены
        if token.is_stop or token.is_space or token.tag_ == "POS" or token.text in ("'", ""):
            continue
        lemma = token.lemma_.strip()
        token_text = token.text.strip()
        if not lemma or not token_text:
            continue
        lemma_map[lemma].add(token_text)  # собираем токены по леммам

    # сохраняем токены
    tokens_path = os.path.join(output_dir, f"{doc_id}_tokens.txt")
    all_tokens = set()
    for toks in lemma_map.values():
        all_tokens.update(toks)

    with open(tokens_path, "w", encoding="utf-8") as out_tokens:
        for t in sorted(all_tokens):
            out_tokens.write(t + "\n")

    # сохраняем леммы + токены
    lemmas_path = os.path.join(output_dir, f"{doc_id}_lemmas.txt")
    with open(lemmas_path, "w", encoding="utf-8") as out_lemmas:
        for lemma in sorted(lemma_map.keys()):
            toks = sorted(lemma_map[lemma])
            if not toks:
                continue
            out_lemmas.write(lemma + " " + " ".join(toks) + "\n")

    print(f"Обработан {filepath} -> {tokens_path}, {lemmas_path}")

print("Готово. Результаты в папке:", output_dir)
