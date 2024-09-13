install:
	poetry install

shell:
	poetry shell



create-migrate:
	poetry run alembic revision --autogenerate -m "Initial migration"
	
migrate:
	poetry run alembic upgrade head


# docker-compose exec postgres bash
# psql -U MGSU -d symposium 
# for connection into database 