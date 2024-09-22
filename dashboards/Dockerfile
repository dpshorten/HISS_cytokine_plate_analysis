FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9999

ENV ON_DOCKER=True
WORKDIR /app/dashboards/
CMD ["python", "app_runner.py", "../parameters/july_2024_data_parameters.yaml"]