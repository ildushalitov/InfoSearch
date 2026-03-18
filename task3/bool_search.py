import spacy
import re
from collections import defaultdict

from spacy.cli import download
# download("en_core_web_sm")  # скачиваем модель если не скачана

INDEX_FILE = 'inverted_index.txt'
URL_FILE = '../task1/pages/index.txt'

print("Loading inverted index...")

# загрузка инвертированного индекса
with open(INDEX_FILE, "r", encoding="utf-8") as f:
    index = defaultdict(set)  # lemma -> множество doc_id
    all_docs = set()  # множество всех документов
    for line in f:
        parts = line.strip().split(' ')
        lemma = parts[0]
        doc_ids = map(int, parts[1:])
        index[lemma].update(doc_ids)
        all_docs.update(index[lemma])

print("Inverted index loaded.")

print("Loading URLs...")

# загрузка индекса doc_id -> url
doc_urls = {}
with open(URL_FILE, "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(' ', 1)
        doc_id = int(parts[0])
        url = parts[1]
        doc_urls[doc_id] = url

print("URLs loaded.")

print("Loading spaCy model...")

# загрузка модели для лемматизации
nlp = spacy.load("en_core_web_sm")

print("Model loaded.\n")

# основной цикл обработки запросов
while True:
    query = input("Query (type 'exit' to quit): ").strip().lower()

    # выход из программы
    if query == "exit" or query == "":
        print("Session finished.")
        break

    # токенизация запроса (слова и скобки)
    tokens = re.findall(r"\w+|\(|\)", query)
    expression = []

    # преобразование запроса в выражение над множествами
    for token in tokens:

        if token == "and":
            expression.append("&")

        elif token == "or":
            expression.append("|")

        elif token == "not":
            expression.append("all_docs -")

        elif token in ("(", ")"):
            expression.append(token)

        else:
            # лемматизация токена
            lemma = nlp(token)[0].lemma_

            # получение множества документов по лемме
            if lemma:
                docs = index.get(lemma, set())
            else:
                docs = set()

            expression.append(f"set({list(docs)})")

    final_expression = " ".join(expression)

    try:
        # вычисление булевого выражения
        result = eval(final_expression)

        print("Doc IDs:", result)

        print("URLs:")
        for doc_id in result:
            if doc_id in doc_urls:
                print(doc_urls[doc_id])

        print()

    except Exception as e:
        print(f"Error in query: {e}\n")
