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
    cargo clippy --workspace --exclude pulsing-py --exclude pulsing-bench-py --all-targets -- -D warnings
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
# CI 环境准备命令 (在各种容器内执行)
# =============================================================================

# --- Manylinux (CentOS) 构建环境 ---
# 用法: docker run --platform linux/arm64 -v $PWD:/workspace -w /workspace \
#       quay.io/pypa/manylinux2014_aarch64 bash -c "just manylinux-setup && just manylinux-build"

# Manylinux 容器内安装构建依赖
manylinux-setup:
    yum install -y gcc gcc-c++ openssl-devel perl-IPC-Cmd
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    . ~/.cargo/env && pip install maturin pytest pytest-asyncio

# Manylinux 容器内构建 wheel
manylinux-build:
    . ~/.cargo/env && maturin build --release --out dist -i /opt/python/cp310-cp310/bin/python3.10 --compatibility manylinux_2_17

# Manylinux 容器内运行测试
manylinux-test:
    pip install dist/*aarch64*.whl && pytest tests/python -v

# --- Fedora 测试环境 ---
# 用法: docker run -v $PWD:/workspace -w /workspace fedora:latest bash -c "just fedora-setup 3.12 && just fedora-test 3.12"

# Fedora 容器内安装 Python 和依赖
fedora-setup python_version="3.12":
    dnf install -y python{{python_version}} python{{python_version}}-pip

# Fedora 容器内安装 wheel 并运行测试
fedora-test python_version="3.12":
    python{{python_version}} -m pip install dist/*.whl
    python{{python_version}} -m pip install pytest pytest-asyncio pytest-cov
    python{{python_version}} -m pytest tests/python -v

# --- Ubuntu/Debian 测试环境 (python:slim 镜像) ---
# 用法: docker run --platform linux/arm64 -v $PWD:/workspace -w /workspace \
#       python:3.12-slim bash -c "just debian-test"

# Debian/Ubuntu slim 容器内安装 wheel 并运行测试
debian-test:
    pip install dist/*.whl
    pip install pytest pytest-asyncio pytest-cov
    pytest tests/python -v

# --- 通用 CI 辅助命令 ---

# 安装 Python 测试依赖
ci-install-test-deps:
    pip install pytest pytest-asyncio pytest-cov

# 安装 wheel 并测试
ci-test-wheel:
    pip install dist/*.whl
    pip install pytest pytest-asyncio pytest-cov
    pytest tests/python -v

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
