.PHONY: help up down demo seed logs build clean

API ?= http://localhost:8080
DOMAIN ?= example.com

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Build and start the stack (db + backend + frontend)
	docker compose up --build -d
	@echo "Frontend: http://localhost:8081   API: $(API)"

down: ## Stop the stack
	docker compose down

build: ## Build all images
	docker compose build

logs: ## Tail backend logs
	docker compose logs -f backend

demo: up ## One-command demo: start the stack, wait for health, seed a mailbox + sample mail
	@echo "Waiting for the API to become healthy..."
	@for i in $$(seq 1 30); do \
	  curl -fsS $(API)/health >/dev/null 2>&1 && break; \
	  sleep 1; \
	done
	@AGENT_MAIL_API_URL=$(API) AGENT_MAIL_EMAIL_DOMAIN=$(DOMAIN) ./scripts/seed_demo.sh

seed: ## Seed a demo instance + sample emails into a running stack
	@AGENT_MAIL_API_URL=$(API) AGENT_MAIL_EMAIL_DOMAIN=$(DOMAIN) ./scripts/seed_demo.sh

clean: ## Stop the stack and remove volumes (drops the database!)
	docker compose down -v
	rm -f maildir/new/*.eml
