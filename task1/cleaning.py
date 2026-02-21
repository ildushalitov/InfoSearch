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
        # Если внутри несколько JSON-объектов — разбиваем и пытаемся парсить
        for chunk in re.split(r'\n(?=\s*[{[]\s*)', text):
            try:
                data = json.loads(chunk)
                results.append(data)
            except Exception:
                continue
    return results


def _find_publish_date_in_scripts(soup: BeautifulSoup) -> Optional[str]:
    for script in soup.find_all('script'):
        text = script.string or script.get_text() or ''
        if not text:
            continue
        m = re.search(r'["\']publishDate["\']\s*:\s*["\']([^"\']+)["\']', text)
        if m:
            return m.group(1)
        m2 = ISO_DT_RE.search(text)
        if m2:
            return m2.group(0)
    time_tag = soup.find('time')
    if time_tag:
        dt = time_tag.get('datetime') or time_tag.get('data-datetime')
        if dt:
            return dt
    return None


def _extract_info_slice_fields(soup: BeautifulSoup) -> List[str]:
    results = []
    # По классам, содержащим ключевые слова
    for el in soup.find_all(class_=lambda c: c and (
            'info-slice' in c.lower() or
            'infoslice' in c.lower() or
            'infoslicelist' in c.lower() or
            'infoslicelistitem' in c.lower()
    )):
        text = ' '.join(el.stripped_strings)
        if text:
            results.append(text)
    # Если ничего не найдено — попытка по data-/aria-атрибутам
    if not results:
        candidates = soup.select('[data-testid*="info"], [data-qa*="info"], [aria-label*="Info"], [aria-label*="info"]')
        for c in candidates:
            t = ' '.join(c.stripped_strings)
            if t:
                results.append(t)
    # Убираем дубликаты, сохраняем порядок
    return list(dict.fromkeys(results))


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
    # ld+json
    ld = _parse_ld_json(soup)
    for item in ld:
        if isinstance(item, dict):
            if item.get('name'):
                name = name or item.get('name')

    # description: meta description / og:description / parsely
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

    publish_date = _get_meta_content(soup, [{'property': 'article:published_time'}, {'name': 'publishDate'},
                                            {'name': 'parsely-post-pubdate'}])
    if not publish_date:
        for item in ld:
            if isinstance(item, dict) and item.get('datePublished'):
                publish_date = item.get('datePublished')
                break
    if not publish_date:
        publish_date = _find_publish_date_in_scripts(soup)

    info_slice_fields = _extract_info_slice_fields(soup)

    return {
        'name': name,
        'description': description,
        'reviewBody': review_body,
        'publishDate': publish_date,
        'infoSliceFields': info_slice_fields
    }


# -----------------------
# Запись всех полей в один файл (без заголовков и без publishDate)
# -----------------------
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

        # infoSliceFields
        items = fields.get('infoSliceFields') or []
        if items:
            for i, it in enumerate(items):
                # записываем каждую запись на новую строку
                f.write(it.strip() + '\n')
        f.write('\n')

        # reviewBody
        if fields.get('reviewBody'):
            f.write(str(fields['reviewBody']).strip())
        # конец файла


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
        # читаем файл (utf-8 или fallback)
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
