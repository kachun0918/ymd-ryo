# Start the bot in the background (-d)
up:
	docker compose up -d --build

# Stop the bot
down:
	docker compose down

# View logs 
logs:
	docker compose logs -f

# Restart everything
restart:
	docker compose down
	docker compose up -d --build

# Clean up unused docker junk
clean:
	docker system prune -f