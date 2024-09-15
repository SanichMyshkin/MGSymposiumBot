install:
	poetry install

shell:
	poetry shell

start:
	poetry run python MGSymposiumBot/main.py

create-migrate:
	poetry run alembic revision --autogenerate -m "Initial migration"
	
migrate:
	poetry run alembic upgrade head


# With Docker
dev:
	docker compose up --build

down:
	docker compose down