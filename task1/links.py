import requests
import time
import re
from bs4 import BeautifulSoup

BASE_URL = "https://pitchfork.com"  # url home страницы pithfork
REVIEWS_URL = BASE_URL + "/reviews/albums/?page={}"  # страницы с списками обзоров на альбомы

session = requests.Session()

links = []
page = 1
pattern = re.compile(r"^/reviews/albums/[a-z0-9\-\._]+/$")  # паттерн url-a обрзора на альбом

while len(links) < 200:

    # проходимся по страницам и собираем ссылки на альбомы

    url = REVIEWS_URL.format(page)
    r = session.get(url, timeout=15)

    if r.status_code != 200:
        print(f"Error {r.status_code} on {page}")
        break

    soup = BeautifulSoup(r.text, "html.parser")
    new_links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if pattern.match(href):  # проверяем что это действительно ссылка на альбом
            full = BASE_URL + href

            if full not in links:
                links.append(full)
                new_links.append(full)

    print(f"Page {page}: {len(new_links)}")

    page += 1
    time.sleep(0.1)

with open("urls.txt", "w", encoding="utf-8") as f:
    for link in links:
        f.write(link + "\n")

print("DONE")
