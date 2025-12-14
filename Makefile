update:
	git pull
	docker compose restart

logs:
	docker compose logs -f --tail=100

deploy:
	git pull
	docker compose up -d --build
	docker system prune -f 

