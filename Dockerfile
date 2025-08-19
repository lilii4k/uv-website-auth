FROM python:3.9
WORKDIR /app
COPY templates static app.py requirements.txt ./
RUN pip install -r requirements.txt
CMD python app.py