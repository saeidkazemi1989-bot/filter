FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data REQUIRE_AUTH=1
WORKDIR /app
RUN useradd --uid 10001 --create-home karnama && mkdir /data && chown karnama:karnama /data
COPY freelance/ ./freelance/
COPY downloads/ ./downloads/
USER karnama
EXPOSE 8000
CMD ["python", "freelance/server.py"]
