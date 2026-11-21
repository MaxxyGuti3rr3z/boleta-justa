FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NUNCA copiar boletas_reales/: contiene boletas con datos personales
COPY src/ src/
COPY web/ web/
COPY datos/ datos/

ENV MODO_PUBLICO=1 PYTHONUNBUFFERED=1
EXPOSE 8101
CMD ["python", "src/api.py"]
