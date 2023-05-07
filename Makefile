start-redis:
	@echo "Starting Redis..."
	docker run --name notionpm-redis -p 6379:6379 -v /root/redis-data:/data -d redis redis-server --save 60 1

start-app:
	@echo "Starting app..."
	python3 -m app.service
