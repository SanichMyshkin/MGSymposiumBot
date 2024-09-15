FROM python:3.11

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
COPY . /app

RUN apt-get update && apt-get install -y make
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install
RUN chmod +x /app/MGSymposiumBot/*.py


EXPOSE 8000

CMD ["make", "start"]