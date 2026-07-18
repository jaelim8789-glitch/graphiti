.PHONY: install format lint test all check mcp-dev mcp-up mcp-down mcp-status dev-setup

# Define variables
PYTHON = python3
UV = uv
PYTEST = $(UV) run pytest
RUFF = $(UV) run ruff
PYRIGHT = $(UV) run pyright

# Default target
all: format lint test

# Install dependencies
install:
	$(UV) sync --extra dev

# Format code
format:
	$(RUFF) check --select I --fix
	$(RUFF) format

# Lint code
lint:
	$(RUFF) check
	$(PYRIGHT) ./graphiti_core 

# Run tests
test:
	DISABLE_FALKORDB=1 DISABLE_KUZU=1 DISABLE_NEPTUNE=1 $(PYTEST) -m "not integration"

# Run format, lint, and test
check: format lint test

# --- MCP / Dev convenience targets ---

# One-shot dev environment setup: deps + Neo4j container
dev-setup: install mcp-up

# Start Neo4j + Graphiti MCP server (local dev stack)
mcp-up:
	docker compose -f mcp_server/docker/docker-compose-neo4j.yml up -d
	@echo "Neo4j: http://localhost:7474  Graphiti MCP: http://127.0.0.1:8001/mcp/"

# Stop dev stack
mcp-down:
	docker compose -f mcp_server/docker/docker-compose-neo4j.yml down

# Show dev stack status
mcp-status:
	docker compose -f mcp_server/docker/docker-compose-neo4j.yml ps
	@echo "--- graphiti mcp port ---"
	@(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/mcp/ 2>/dev/null || echo "port 8001 not listening")

# Run MCP server in foreground (for debugging)
mcp-dev:
	$(UV) run uvicorn mcp_server.main:app --host 127.0.0.1 --port 8001 --reload
