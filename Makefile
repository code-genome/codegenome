image = cg-worker
image-dev = cg-dev
image-ui = cg-ui

docker-build-worker : docker/Dockerfile
	# git pull
	docker build -f docker/Dockerfile --build-arg HOST_UID=1001 -t $(image) .

docker-build-ui :
	cd /tmp/ && rm -rf /tmp/codegenome_ui && \
	git clone https://github.com/code-genome/codegenome_ui.git && \
	cd codegenome_ui && \
	docker build -t $(image-ui) . &&\
	cd /tmp/ && rm -rf /tmp/codegenome_ui

docker-builds : docker-build-worker docker-build-ui
	#none

docker-builds-remove:
	docker rm $(image) &>/dev/null
	docker rm $(image-ui) &>/dev/null
	docker image rm $(image) &>/dev/null
	docker image rm $(image-ui) &>/dev/null

start_local :
	mkdir -p $(shell echo ~)/.cg

	#run worker 
	docker run --rm -d -u 1001:1001 -p 5001:5001 -v  $(shell echo ~)/.cg:/home/cguser/.cg --name $(image) $(image)

	#run ui
	docker run --rm -d -p 5000:5000 --add-host host.docker.internal:host-gateway -e CG_HOST="http://host.docker.internal:5001" --name $(image-ui) $(image-ui)

start_worker :
	mkdir -p $(shell echo ~)/.cg

	#run worker 
	docker run --rm -d -u 1001:1001 -p 5001:5001 -v  $(shell echo ~)/.cg:/home/cguser/.cg --name $(image) ghcr.io/code-genome/cg-worker:latest

start_ui :
	#run ui
	docker run --rm -d -p 5000:5000 --add-host host.docker.internal:host-gateway -e CG_HOST="http://host.docker.internal:5001" --name $(image-ui) ghcr.io/code-genome/cg-ui:latest

start : start_worker start_ui

stop : 
	docker stop $(image)
	docker stop $(image-ui)

deps :
	cd docker
	sudo bash install_all_local.sh

docker-build-dev : docker/Dockerfile.dev
	docker build -f docker/Dockerfile.dev --build-arg HOST_UID=$(shell id -u) -t $(image-dev) .

dev-cli : 
	docker run --rm -v $(shell pwd):/cg -t -i --entrypoint /bin/bash $(image-dev)

pre-commit :
	pre-commit run --all-files
