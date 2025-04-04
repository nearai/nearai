FROM rust:1.85-slim AS builder

# Add the linux/amd64 target
RUN rustup target add x86_64-unknown-linux-gnu

WORKDIR /usr/src/app

# Install build dependencies including cross-compilation tools
RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev build-essential crossbuild-essential-amd64 && \
    rm -rf /var/lib/apt/lists/*

# Tell Cargo to use the proper linker for the x86_64 target.
ENV CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=x86_64-linux-gnu-gcc

# Copy the entire project.
COPY . .

# Build the application for linux/amd64.
RUN cargo build --release --target=x86_64-unknown-linux-gnu

# ---- Runtime stage ----
FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y ca-certificates libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the built binary from the builder stage.
COPY --from=builder /usr/src/app/target/x86_64-unknown-linux-gnu/release/ /usr/local/bin/

ENV RUST_LOG=info
EXPOSE 3000
CMD ["guest_manager"]
