FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9999

WORKDIR /app/dashboards/individual_patients
CMD ["python", "individual_patients_dashboard.py", "../../parameters/docker_dashboard_parameters.yaml"]