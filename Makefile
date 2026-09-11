.PHONY: proto rust run-rust run-python run-voice run-all run-all-no-voice docker-build docker-up docker-down clean

PROTO_DIR = proto
RUST_DIR = rust-engine
PY_PROTO_DIR = app/proto

# Generate protobuf stubs
proto:
	@echo "=== Generating Python protobuf stubs ==="
	python -m grpc_tools.protoc \
		-I$(PROTO_DIR) \
		--python_out=$(PY_PROTO_DIR) \
		--grpc_python_out=$(PY_PROTO_DIR) \
		$(PROTO_DIR)/audio_stream.proto
	@echo "# Generated — do not edit" > $(PY_PROTO_DIR)/__init__.py
	@echo "=== Done ==="

# Build the Rust audio engine
rust:
	@echo "=== Building Rust audio engine ==="
	cd $(RUST_DIR) && cargo build --release
	@echo "=== Done ==="

# Run just the Rust engine
run-rust:
	cd $(RUST_DIR) && cargo run --release

# Run just the Python FastAPI app (chat only, no voice)
run-python:
	uvicorn cohost_bot:app --reload

# Run voice pipeline only (mic -> VAD -> STT -> LLM -> TTS)
run-voice:
	python run_audio.py

# Start everything: Rust + FastAPI + voice + YouTube
run-all: rust
	python run.py

# Start everything except voice (chat + YouTube only)
run-all-no-voice: rust
	python run.py --no-voice

# Docker: build all images
docker-build:
	docker compose build

# Docker: start all services
docker-up:
	docker compose up -d

# Docker: stop all services
docker-down:
	docker compose down

# Clean build artifacts
clean:
	cd $(RUST_DIR) && cargo clean
	rm -rf $(PY_PROTO_DIR)/*_pb2*.py $(PY_PROTO_DIR)/__init__.py
