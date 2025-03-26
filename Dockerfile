FROM python:3.11


WORKDIR /app


COPY . .

RUN python -m venv /opt/venv


RUN python -m venv /opt/venv


RUN /opt/venv/bin/python -m pip install --upgrade pip
RUN /opt/venv/bin/python -m pip install -e . --no-build-isolation

