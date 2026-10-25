# Alfa News Analytics

Персонализированная новостная аналитика для крупного бизнеса.

## Технологии

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- LLM Gateway

## Требования

- Python 3.11 или совместимая с зависимостями версия
- PostgreSQL
- Git

## Установка

Клонируйте репозиторий и перейдите в папку проекта:

```bash
git clone https://github.com/qvgenia/alfa-news-analytics.git
cd alfa-news-analytics/alfa-business-analytics
```

Создайте и активируйте виртуальное окружение.

Windows (Git Bash):

```bash
python -m venv .venv
source .venv/Scripts/activate
```

Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

## Настройка окружения

Создайте локальный файл `.env` на основе шаблона:

```bash
cp .env.example .env
```

Отредактируйте `.env` и укажите параметры подключения к PostgreSQL: `DATABASE_URL` либо настройки `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` и `POSTGRES_DB`.

Для интеграции с LLM Gateway заполните поддерживаемые проектом параметры: адрес `LLM_BASE_URL`, API-ключ `LLM_API_KEY`, провайдера и названия моделей. Фактические значения необходимо получить у команды проекта или администратора Gateway.

**Не добавляйте `.env` и реальные API-ключи в Git.** Для примера конфигурации предназначен файл `.env.example`.

## Миграции базы данных

При настроенном подключении к PostgreSQL выполните:

```bash
alembic upgrade head
```

## Запуск API

Из каталога `alfa-business-analytics` выполните:

```bash
uvicorn app.main:app --reload
```

Адрес локального API по умолчанию: `http://127.0.0.1:8000`.

Интерактивная документация API доступна по адресу `http://127.0.0.1:8000/docs`.

## Тесты

```bash
python -m pytest -q
```

## Команда

- Role A: профили клиентов и база данных
- Role B: получение новостей и RAG
- Role C: LLM Gateway, агент и интерфейс
