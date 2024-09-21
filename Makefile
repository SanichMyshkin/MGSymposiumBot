install:
	poetry install

shell:
	poetry shell

start:
	docker compose up -d --build 

stop:
	docker compose down
