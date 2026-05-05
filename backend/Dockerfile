FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FOOD_DATASET_PATH=/app/food_dataset_fixed.csv
ENV RAW_DATA_PATH=/app/food_dataset_fixed.csv
ENV SCALED_DATA_PATH=/app/food_dataset_fixed.csv

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app/backend
COPY nutrigain_recommender.py /app/nutrigain_recommender.py
COPY data/food_dataset_fixed.csv /app/food_dataset_fixed.csv

ENV PYTHONPATH=/app:/app/backend
WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
