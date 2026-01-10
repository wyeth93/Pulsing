# Justfile for Pulsing

# Default target
default: dev

# =============================================================================
# Development
# =============================================================================

# Install all packages in development mode
dev:
    @echo "Building core..."
    maturin develop
    @echo "Building benchmarks..."
    maturin develop --manifest-path crates/pulsing-bench-py/Cargo.toml
    @echo "Ready to code!"

# Build release wheels
build:
    maturin build --release
    maturin build --release --manifest-path crates/pulsing-bench-py/Cargo.toml

# =============================================================================
# Testing & QA
# =============================================================================

# Run all tests
test: test-rust test-python

# Run Rust tests
test-rust:
    cargo test --workspace --exclude pulsing-bench-py --exclude pulsing-py

# Run Python tests
test-python:
    pytest tests/python --ignore=tests/python/test_chaos.py

# Run Chaos tests (separated because they are slower/flakier)
test-chaos:
    pytest tests/python/test_chaos.py

# Format all code (Rust + Python)
fmt:
    cargo fmt
    ruff format .

# Lint all code
lint:
    cargo clippy --workspace -- -D warnings
    ruff check .

# =============================================================================
# Coverage (本地查看覆盖率)
# =============================================================================

# Run all coverage reports
cov: cov-rust cov-python
    @echo ""
    @echo "Coverage reports generated!"
    @echo "  Rust:   target/llvm-cov/html/index.html"
    @echo "  Python: htmlcov/index.html"
    @echo ""
    @echo "Run 'just cov-open' to open in browser"

# Rust coverage with HTML report
cov-rust:
    @echo "Running Rust tests with coverage..."
    cargo llvm-cov --workspace --exclude pulsing-py --exclude pulsing-bench-py --html
    @echo "Report: target/llvm-cov/html/index.html"

# Rust coverage summary (terminal only, no HTML)
cov-rust-summary:
    cargo llvm-cov --workspace --exclude pulsing-py --exclude pulsing-bench-py

# Rust coverage with nightly (支持 #[coverage(off)] 标记，但可能不稳定)
cov-rust-nightly:
    @echo "Running Rust tests with coverage (nightly)..."
    cargo +nightly llvm-cov --workspace --exclude pulsing-py --exclude pulsing-bench-py --html
    @echo "Report: target/llvm-cov/html/index.html"

# Python coverage with HTML report
cov-python:
    @echo "Running Python tests with coverage..."
    pytest tests/python --ignore=tests/python/test_chaos.py --cov=python/pulsing --cov-report=html --cov-report=term
    @echo "Report: htmlcov/index.html"

# Open coverage reports in browser (macOS/Linux)
cov-open:
    #!/usr/bin/env bash
    if [ -f target/llvm-cov/html/index.html ]; then \
        echo "Opening Rust coverage report..."; \
        open target/llvm-cov/html/index.html 2>/dev/null || xdg-open target/llvm-cov/html/index.html 2>/dev/null; \
    fi
    if [ -f htmlcov/index.html ]; then \
        echo "Opening Python coverage report..."; \
        open htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null; \
    fi

# =============================================================================
# Maintenance
# =============================================================================

# Clean build artifacts
clean:
    cargo clean
    rm -rf target/
    rm -rf **/*.so
    rm -rf **/*.pyd
    rm -rf htmlcov/
    rm -rf .coverage
