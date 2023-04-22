restart-redis:
	@echo "Stopping Redis..."
	docker stop notionpm-redis

	@echo "Removing Redis..."
	docker rm notionpm-redis

	@echo "Starting Redis..."
	docker run --name notionpm-redis -d -p 6379:6379 redis

start-app:
	@echo "Starting app..."
	python3 -m app.server

restart-all:
	@echo "Stopping Redis..."
	docker stop notionpm-redis

	@echo "Removing Redis..."
	docker rm notionpm-redis

	@echo "Starting Redis..."
	docker run --name notionpm-redis -d -p 6379:6379 redis

	@echo "Starting app..."
	python3 -m app.server
