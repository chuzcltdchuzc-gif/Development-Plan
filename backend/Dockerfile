FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY . .
RUN pip install --upgrade pip && pip install .

EXPOSE 8000

# --no-proxy-headers: this deployment has no configured trusted-reverse-proxy
# allowlist (ADR-004), so X-Forwarded-For/-Proto must never be trusted at the
# ASGI-server layer either — confirmed against a live server that uvicorn's
# default (proxy_headers=True, forwarded_allow_ips="127.0.0.1") rewrites
# request.client from a client-supplied header for any peer connecting from
# 127.0.0.1, silently defeating app.kernel.security.http_hardening's own
# "trust only request.client.host" rate-limiter fix one layer below it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
