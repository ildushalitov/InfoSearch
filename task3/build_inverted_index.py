from collections import defaultdict
import os

TERMS_DIR = '../task2/processed_txts'  # папка с леммами

inverted_index = defaultdict(set)  # словарь для индекса. ключ -- лемма, значение -- номера доков

for filename in os.listdir(TERMS_DIR):

    if not filename.endswith('lemmas.txt'):  # берем только файлы с леммами
        continue

    doc_id = int(filename.split('_')[0])
    file_path = os.path.join(TERMS_DIR, filename)

    with open(file_path, "r", encoding="utf-8") as f:

        print('Processing ' + filename)
        for line in f:  # проходимся по всем строкам

            lemma = line.strip().split(' ')[0]  # берем первое слово в строке -- лемму
            inverted_index[lemma].add(doc_id)  # кладем в сет номер дока в котором встречается данная лемма

with open('inverted_index.txt', "w", encoding="utf-8") as f:  # сохраянем индекс в файл
    for lemma in sorted(inverted_index.keys()):
        f.write(lemma + " " + " ".join(map(str, sorted(inverted_index[lemma]))) + "\n")