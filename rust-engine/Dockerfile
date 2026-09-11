FROM rust:1.82-slim AS builder

WORKDIR /app

COPY rust-engine/Cargo.toml rust-engine/Cargo.lock* ./

# Create dummy src to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cd /app && cargo build --release 2>/dev/null || true
RUN rm -rf src

COPY rust-engine/ .

RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/audio-engine /usr/local/bin/audio-engine

EXPOSE 50051

CMD ["audio-engine"]
