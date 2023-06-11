start-app:
	@echo "Starting app..."
	python3 -m app.service

start-tracker:
	@echo "Starting tracking..."
	python3 -m app.track

dc-build:
	@echo "Building from docker-compose.yml ..."
	docker compose build

dc-start:
	@echo "Starting from docker-compose.yml ..."
	docker compose up -d
