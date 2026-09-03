FROM python:3.12-slim

WORKDIR /app

# No apt-get step needed — psycopg2-binary ships as a precompiled wheel,
# so gcc/libpq-dev (only needed to build psycopg2 from source) are dead
# weight here. Removing this also sidesteps flaky Debian mirror timeouts
# on unrelated packages during build.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
