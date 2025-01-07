Set up the environment by copying `.env.example` to `.env.local` and filling in the required values:
```
docker build . -t voice-pipeline-agent-python:main-agentName

docker run -d --name voice-pipeline-lawyer-agent-python \
  --net=host \
  -v env.local:/voice-pipeline-agent-python/.env.local \
  voice-pipeline-agent-python:main-agentName
```
