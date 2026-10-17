FROM python:3.12-alpine
WORKDIR /app
COPY simulation /app/simulation
RUN addgroup -S app && adduser -S -G app app && mkdir /state && chown app:app /state
USER app
ENV LIVE_DB_PATH=/state/live.sqlite3
CMD ["python", "-m", "simulation.live_stack.service"]
