import requests
import os
from tqdm import tqdm

with open("urls.txt", "r", encoding="utf-8") as f:
    urls = [line.strip() for line in f if line.strip()]  # перекалдываем ссылки из txt файла в список

session = requests.Session()  # создзаем сессию
index_lines = []
file_id = 1
for url in tqdm(urls, desc="Скачивание"):  # обходим сайты из списка
    r = session.get(url, timeout=20)
    if r.status_code != 200:  # проверка статуса ответа
        print("status_code != 200")
        break
    filename = os.path.join("pages", f"{file_id}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(r.text)  # записываем содердимое страницы в файл
    index_lines.append(f"{file_id} {url}")
    file_id += 1

index_path = os.path.join("pages", "index.txt")
with open(index_path, "w", encoding="utf-8") as f:
    f.write("\n".join(index_lines))
