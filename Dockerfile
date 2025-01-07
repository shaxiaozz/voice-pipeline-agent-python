FROM python:3.12.3
WORKDIR /voice-pipeline-agent-python
COPY . .
RUN pip install -r requirements.txt
CMD ["python","/voice-pipeline-agent-python/agent.py","dev"]