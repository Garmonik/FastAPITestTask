bash
```shell
  sudo docker-compose up --build
```
ИЛИ
bash
```shell
  pipenv shell
  python3 main.py
```


Пример запросов
1) Запрос:
```
curl -X 'POST'   'http://127.0.0.1:8000/reviews'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '{
  "text": "плохая"
}'
```
Ответ:
```
{ 
  "id":5,
  "text":"плохая",
  "sentiment":"negative",
  "created_at":"2025-07-23T02:56:39.428287+00:00"
}
```
2) Запрос
```
curl -X 'GET'   'http://127.0.0.1:8000/reviews'   -H 'accept: application/json'
```
Ответ
```
[
  {
    "id":1,
    "text":"хорошая",
    "sentiment":"positive",
    "created_at":"2025-07-23T01:47:26.477327+00:00"
  },
  {
    "id":2,
    "text":"string",
    "sentiment":"neutral",
    "created_at":"2025-07-23T02:21:25.382955+00:00"
  },
  {
    "id":3,
    "text":"плохая",
    "sentiment":"negative",
    "created_at":"2025-07-23T02:28:40.294827+00:00"
  },
  {
    "id":4,
    "text":"плохая",
    "sentiment":"negative",
    "created_at":"2025-07-23T02:46:16.250532+00:00"
  },
  {
    "id":5,
    "text":"плохая",
    "sentiment":"negative",
    "created_at":"2025-07-23T02:56:39.428287+00:00"
  }
  ]
```

3) Запрос
```
curl -X 'GET' \
  'http://127.0.0.1:8000/reviews?sentiment=positive' \
  -H 'accept: application/json'
```

Ответ

```
[
  {
    "id":1,
    "text":"хорошая",
    "sentiment":"positive",
    "created_at":"2025-07-23T01:47:26.477327+00:00"
  }
]
```

## Предложения для доработки
1) Разделить код по файлам:
   1) переменные окружения и логгер в файл config.py
   2) инициализацию базы данных в файл database.py
   3) модели для базы данных в models.py
   4) функция для проверки отзыва в файл checkup.py
2) Добавить пагинацию для list_reviews
3) Изменить тип created_at с TEXT на DATETIME