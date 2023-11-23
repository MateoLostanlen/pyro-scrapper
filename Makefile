# this target runs checks on all files
quality:
	isort . -c
	flake8
	mypy
	pydocstyle
	black --check .

# this target runs checks on all files and potentially modifies some of them
style:
	isort .
	black .

# Build the docker
docker:
	docker build . -t pyronear/pyro-scrapper:python3.8.1-slim

# Run the scrapper wrapper
run:
	docker build . -t pyronear/pyro-scrapper:latest
	docker-compose up -d

# Get log from scrapper wrapper
log: 
	docker logs -f --tail 50 pyro-scrapper_pyro-scrapper_1

# Stop the scrapper wrapper
stop:
	docker-compose down
