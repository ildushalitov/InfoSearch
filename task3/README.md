# Задание 3 

- **build_inverted_index.py** — строит инвертированный индекс на основе файлов с леммами в ***../task2/processed_txts*** и сохраняет его в ***inverted_index.txt***
- **bool_search.py** — реализация буелва поиска 

## Deployment Manual
1. Установить spacy:
```bash
pip install spacy
```
2. Запустить **bool_search.py**
3. Дождаться строки ввода 
```
Query (type 'exit' to quit): 
```
и ввести запрос, например: 
``` 
(post AND hardcore) AND NOT (midwest AND emo)
```
в результате выведутся номера подходящих документов, а также url-ы их страниц