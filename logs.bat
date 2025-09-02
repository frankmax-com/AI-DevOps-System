@echo off
echo Viewing AI Provider Agent Service logs...

REM Show logs for all services
docker-compose logs -f

REM To view logs for specific service, use:
REM docker-compose logs -f ai-provider-agent
REM docker-compose logs -f redis
REM docker-compose logs -f prometheus
REM docker-compose logs -f grafana
