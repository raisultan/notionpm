start-app:
	@echo "Starting app..."
	python3 -m app.service

dc-build:
	@echo "Building from docker-compose.yml ..."
	docker compose build

dc-start:
	@echo "Starting from docker-compose.yml ..."
	docker compose up -d

dc-rebuild-app:
	@echo "Rebuilding app from docker-compose.yml ..."
	docker compose build app
	@echo "Starting app from docker-compose.yml ..."
	docker compose up -d app
