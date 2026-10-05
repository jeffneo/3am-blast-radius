# 3 a.m. Blast Radius: shortcuts. `make help` lists them.
# Credentials and ports come from .env (copy .env.example). Never echo them here.

include .env
export

.PHONY: help up down reset load build verify verify-plain verify-dev docs rehearsal rehearsal-down shell logs urls

help:
	@echo "make up          start Neo4j (APOC + GDS Enterprise) and Enterprise Studio"
	@echo "make load        load graph/load.cypher into the '$(NEO4J_DATABASE)' database"
	@echo "make build       regenerate the graph, score it with GDS, reload (build/build.sh)"
	@echo "make verify      all queries on a clean Neo4j 5.26 (the lab target); needs Docker"
	@echo "make verify-plain  the same on a server WITHOUT the GDS plugin (skips the GDS statements)"
	@echo "make verify-dev  the same checks on the dev server version ($(NEO4J_IMAGE))"
	@echo "make docs        regenerate README, STORYLINE, MODEL, the lab and facilitator guides and their PDFs from the recorded results"
	@echo "make rehearsal  N attendee-shaped databases (lab-user01..) on the dev stack, to rehearse Part 4 together: make rehearsal N=4"
	@echo "make rehearsal-down  drop them again"
	@echo "make shell       cypher-shell on the lab database"
	@echo "make logs        follow the Neo4j log"
	@echo "make urls        where everything is"
	@echo "make down        stop everything, keep the data"
	@echo "make reset       stop everything and DELETE the data volumes"

up:
	docker compose up -d
	@$(MAKE) --no-print-directory urls

load:
	docker compose run --rm loader

build:
	./build/build.sh

verify:
	python3 build/verify.py

verify-plain:
	python3 build/verify.py --no-gds

verify-dev:
	python3 build/verify.py --image $(NEO4J_IMAGE)

docs:
	python3 build/make_guide.py
	uv run --with markdown build/make_pdf.py

N ?= 4
rehearsal:
	build/rehearsal.sh up $(N)

rehearsal-down:
	build/rehearsal.sh down $(N)

shell:
	@docker exec -it br-neo4j sh -c 'cypher-shell -u "$${NEO4J_AUTH%%/*}" -p "$${NEO4J_AUTH#*/}" -d $(NEO4J_DATABASE)'

logs:
	docker compose logs -f neo4j

urls:
	@echo "Neo4j Browser      http://localhost:$(NEO4J_HTTP_PORT)"
	@echo "Enterprise Studio  http://localhost:$(NES_PORT)   (deployment: Blast Radius)"
	@echo "Bolt               bolt://localhost:$(NEO4J_BOLT_PORT)"
	@echo "Database           $(NEO4J_DATABASE) (the default, so every client opens on it)"
	@echo "Credentials        in .env"

down:
	docker compose down

reset:
	@read -p "Delete the Neo4j data volumes (the graph and Studio assets)? [y/N] " a; [ "$$a" = y ] || { echo aborted; exit 1; }
	docker compose down -v
