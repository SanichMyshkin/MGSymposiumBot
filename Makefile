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


# docker-compose exec postgres bash
# psql -U MGSU -d symposium 
# for connection into database 

# docker-compose run app /bin/sh