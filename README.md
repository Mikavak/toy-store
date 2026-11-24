# Toy Store

MVP интернет-магазина детских игрушек на Django.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_store
python manage.py runserver
```

Административная панель доступна по адресу `http://127.0.0.1:8000/admin/`.

## Тесты

```bash
python manage.py test catalog
```
