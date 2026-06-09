PROJECT_ID   ?= your-gcp-project-id
REGION       ?= us-central1
IMAGE        := gcr.io/$(PROJECT_ID)/finsentinel:latest
SERVICE      := finsentinel

.PHONY: install dev seed build deploy

install:
	pip install -r requirements.txt
	cd frontend && npm install

dev:
	@echo "Starting backend + frontend..."
	cd frontend && npm run dev &
	uvicorn backend.main:app --reload --port 8000

seed:
	python backend/seed_data.py

build:
	docker build -f infra/Dockerfile -t $(IMAGE) .

deploy:
	gcloud builds submit --tag $(IMAGE) --project $(PROJECT_ID)
	gcloud run deploy $(SERVICE) \
	  --image $(IMAGE) \
	  --region $(REGION) \
	  --platform managed \
	  --allow-unauthenticated \
	  --set-env-vars MONGODB_URI=$(MONGODB_URI),GOOGLE_CLOUD_PROJECT=$(PROJECT_ID) \
	  --project $(PROJECT_ID)

logs:
	gcloud run services logs tail $(SERVICE) --region $(REGION) --project $(PROJECT_ID)
