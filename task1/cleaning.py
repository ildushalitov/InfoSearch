from pathlib import Path
import re
import json
from typing import List, Optional, Any, Dict
from bs4 import BeautifulSoup

# Папки вход/выход
PAGES_DIR = Path('pages')
CLEANED_DIR = Path('cleaned')
CLEANED_DIR.mkdir(exist_ok=True)

ISO_DT_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z')


# -----------------------
# Вспомогательные функции
# -----------------------
def _get_meta_content(soup: BeautifulSoup, key_names: List[dict]) -> Optional[str]:
    for attrs in key_names:
        tag = soup.find('meta', attrs=attrs)
        if tag and tag.get('content'):
            return tag['content'].strip()
    return None


def _parse_ld_json(soup: BeautifulSoup) -> List[Any]:
    results = []
    for script in soup.find_all('script', type='application/ld+json'):
        text = script.string or script.get_text() or ''
        text = text.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
            results.append(data)
            continue
        except Exception:
            pass
        for chunk in re.split(r'\n(?=\s*[{[]\s*)', text):
            try:
                data = json.loads(chunk)
                results.append(data)
            except Exception:
                continue
    return results


def _extract_info_slice_fields(soup: BeautifulSoup) -> List[str]:
    results = []
    for el in soup.find_all(class_=lambda c: c and (
            'info-slice' in c.lower() or
            'infoslice' in c.lower() or
            'infoslicelist' in c.lower() or
            'infoslicelistitem' in c.lower() or
            'infoslice' in c.lower()
    )):
        text = ' '.join(el.stripped_strings)
        if text:
            results.append(text)

    if not results:
        candidates = soup.select('[data-testid*="info"], [data-qa*="info"], [aria-label*="Info"], [aria-label*="info"]')
        for c in candidates:
            t = ' '.join(c.stripped_strings)
            if t:
                results.append(t)
    # Убираем дубликаты, сохраняем порядок
    return list(dict.fromkeys(results))


def _extract_author_names(soup: BeautifulSoup) -> List[str]:
    authors: List[str] = []


    meta_author = _get_meta_content(soup,
                                    [{'name': 'author'}, {'property': 'article:author'}, {'name': 'parsely-author'}])
    if meta_author:

        for part in re.split(r'\s*[;,/]\s*|\s+and\s+', meta_author):
            name = part.strip()
            if name:
                authors.append(name)

    ld = _parse_ld_json(soup)
    for item in ld:
        if isinstance(item, dict) and item.get('author'):
            a = item.get('author')

            if isinstance(a, str):
                authors.append(a.strip())
            elif isinstance(a, dict):

                name = a.get('name') or a.get('author') or None
                if name:
                    authors.append(str(name).strip())
            elif isinstance(a, list):
                for elt in a:
                    if isinstance(elt, str):
                        authors.append(elt.strip())
                    elif isinstance(elt, dict):
                        name = elt.get('name') or elt.get('author')
                        if name:
                            authors.append(str(name).strip())


    for el in soup.find_all(attrs={'itemprop': 'author'}):

        text = ' '.join(el.stripped_strings)
        if text:
            authors.append(text.strip())
    # По классам и атрибутам rel
    for el in soup.find_all(lambda tag: (
                                                tag.get('rel') and ('author' in ' '.join(tag.get('rel')))) or
                                        (tag.has_attr('class') and any(
                                            'author' in c.lower() or 'byline' in c.lower() or 'contributor' in c.lower()
                                            for c in tag.get('class')))
                            ):
        txt = ' '.join(el.stripped_strings)
        if txt:
            authors.append(txt.strip())

    for sel in ['a[rel="author"]', '.byline', '.article-author', '.author-name', '.author']:
        for el in soup.select(sel):
            txt = ' '.join(el.stripped_strings)
            if txt:
                authors.append(txt.strip())

    for el in soup.find_all(['p', 'div', 'span', 'a', 'li']):
        txt = el.get_text(strip=True)
        if not txt or len(txt) > 200:
            continue

        m = re.match(r'^(By|by)\s+([A-Z][\w\-\.\s]+)$', txt)
        if m:
            authors.append(m.group(2).strip())
            continue

        m2 = re.match(r'^(Автор[:\-–]\s*)(.+)$', txt, flags=re.I)
        if m2:
            authors.append(m2.group(2).strip())
            continue

    clean: List[str] = []
    for a in authors:
        name = re.sub(r'\s+', ' ', a).strip()
        if name and name not in clean:
            clean.append(name)
    return clean


# -----------------------
# Основная функция извлечения
# -----------------------
def extract_fields_from_html(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'html.parser')

    # name: meta og:title / meta title / <title> / h1 / ld+json
    name = _get_meta_content(soup, [{'property': 'og:title'}, {'name': 'title'}])
    if not name and soup.title and soup.title.string:
        name = soup.title.string.strip()
    if not name:
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
    # ld+json — дополнительная попытка
    ld = _parse_ld_json(soup)
    for item in ld:
        if isinstance(item, dict) and not name:
            if item.get('name'):
                name = item.get('name')

    description = _get_meta_content(soup, [{'name': 'description'}, {'property': 'og:description'},
                                           {'name': 'parsely-metadata'}])
    if description and description.strip().startswith('{') and 'description' in description:
        try:
            parsed = json.loads(description)
            if isinstance(parsed, dict) and parsed.get('description'):
                description = parsed.get('description')
        except Exception:
            pass

    review_body = None
    for item in ld:
        if isinstance(item, dict):
            if item.get('reviewBody'):
                review_body = item.get('reviewBody')
                break
            if item.get('articleBody'):
                review_body = item.get('articleBody')
                break

    if not review_body:
        el = soup.find(attrs={'itemprop': 'reviewBody'}) or soup.find(attrs={'itemprop': 'articleBody'})
        if el:
            paragraphs = el.find_all(['p', 'div'])
            if paragraphs:
                review_body = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            else:
                review_body = el.get_text(separator='\n', strip=True)

    if not review_body:
        article = soup.find('article') or soup.find(attrs={'role': 'article'}) or soup.find('main')
        if article:
            paragraphs = article.find_all('p')
            if paragraphs:
                review_body = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            else:
                review_body = article.get_text(separator='\n', strip=True)

    # info slice
    info_slice_fields = _extract_info_slice_fields(soup)

    # author names
    author_names = _extract_author_names(soup)

    return {
        'name': name,
        'description': description,
        'authorNames': author_names,
        'reviewBody': review_body,
        'infoSliceFields': info_slice_fields
    }


def write_single_cleaned_file(out_path: Path, fields: Dict[str, Any]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        # name
        if fields.get('name'):
            f.write(str(fields['name']).strip())
        f.write('\n\n')

        # description
        if fields.get('description'):
            f.write(str(fields['description']).strip())
        f.write('\n\n')

        # authorNames
        authors = fields.get('authorNames') or []
        if authors:
            for a in authors:
                f.write(a.strip() + '\n')
        f.write('\n')

        # infoSliceFields
        items = fields.get('infoSliceFields') or []
        if items:
            for it in items:
                f.write(it.strip() + '\n')
        f.write('\n')

        # reviewBody
        if fields.get('reviewBody'):
            f.write(str(fields['reviewBody']).strip())


# -----------------------
# Обход папки pages
# -----------------------
def process_all_pages(pages_dir: Path, cleaned_dir: Path):

    if not pages_dir.exists() or not pages_dir.is_dir():
        print(f'Входная папка {pages_dir!s} не найдена. Поместите HTML-файлы в папку "{pages_dir}" и запустите снова.')
        return

    files = sorted([p for p in pages_dir.iterdir() if p.is_file()])
    if not files:
        print(f'Файлы в папке {pages_dir!s} не найдены.')
        return

    for file_path in files:
        try:
            try:
                html = file_path.read_text(encoding='utf-8')
            except Exception:
                html = file_path.read_text(encoding='latin-1', errors='ignore')
        except Exception as e:
            print(f'Не удалось прочитать {file_path.name}: {e}')
            continue

        print(f'Обрабатываю: {file_path.name}')
        fields = extract_fields_from_html(html)

        out_name = file_path.stem + '.txt'
        out_path = cleaned_dir / out_name
        write_single_cleaned_file(out_path, fields)

    print('Обработка завершена. Результаты в папке:', cleaned_dir.resolve())


# -----------------------
# Запуск
# -----------------------
if __name__ == '__main__':
    process_all_pages(PAGES_DIR, CLEANED_DIR)
