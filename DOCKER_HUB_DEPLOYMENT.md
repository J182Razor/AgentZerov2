# Deploying Agent Zero with Swarm Enhancements to Docker Hub

This guide explains how to build and deploy the enhanced Agent Zero framework with swarm capabilities to your Docker Hub repository.

## Prerequisites

1. Docker installed and running on your system
2. Docker Hub account (username: johnlawal)
3. Docker Hub access token (dckr_pat_9L227TJ2lbKWx0SQYwB6v4Q4m3c)

## Building the Docker Image

1. Navigate to the Agent Zero root directory:
   ```bash
   cd /a0
   ```

2. Build the Docker image with the swarm enhancements:
   ```bash
   docker build -f Dockerfile.swarm -t agentzeroswarm:latest .
   ```

## Tagging for Docker Hub

Tag the image for your Docker Hub repository:
   ```bash
   docker tag agentzeroswarm:latest johnlawal/agentzeroswarm:latest
   ```

## Pushing to Docker Hub

1. Login to Docker Hub using your access token:
   ```bash
   docker login -u johnlawal -p dckr_pat_9L227TJ2lbKWx0SQYwB6v4Q4m3c
   ```

2. Push the image to Docker Hub:
   ```bash
   docker push johnlawal/agentzeroswarm:latest
   ```

## Running the Enhanced Agent Zero Container

After pushing to Docker Hub, you can run the enhanced Agent Zero container:

```bash
docker run -d \
  --name agent-zero-swarm \
  -p 50080:80 \
  -v /path/to/your/data:/a0/usr \
  johnlawal/agentzeroswarm:latest
```

Replace `/path/to/your/data` with the path where you want to store persistent data.

## Verification

1. Check that the image was pushed successfully:
   ```bash
   docker search johnlawal/agentzeroswarm
   ```

2. Verify the container is running:
   ```bash
   docker ps
   ```

3. Access the Web UI at `http://localhost:50080`

## Additional Notes

- The enhanced Agent Zero includes all swarm patterns:
  - LLM Council and Debate with Judge
  - Swarm Router, RoundRobinSwarm, GroupChat
  - ForestSwarm, SpreadSheetSwarm, AutoSwarmBuilder

- All new tools are documented in:
  - `/a0/prompts/default/tools/swarm_consensus.md`
  - `/a0/prompts/default/tools/swarm_patterns.md`

- The image is built on top of the official Agent Zero base image
