# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Applies migrations to the database running in Docker
docker-apply-migrations:
	cd ./migrations && \
	for f in $$(ls *.sql | sort); do \
		echo "Applying $$f"; \
		docker exec -i mysql mysql -u$(DATABASE_USER) -p$(DATABASE_PASSWORD) -h$(DATABASE_HOST) < $$f || exit 1; \
	done

apply-migrations:
	cd ./migrations && \
	for f in $$(ls *.sql | sort); do \
		echo "Applying $$f"; \
		mysql -u$(DATABASE_USER) -p$(DATABASE_PASSWORD) -h$(DATABASE_HOST) < $$f || exit 1; \
	done