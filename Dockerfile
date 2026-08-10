FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY configs ./configs

RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000

CMD ["uvicorn", "story_game.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
