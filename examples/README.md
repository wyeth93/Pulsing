# Pulsing Examples

本目录包含 Pulsing Actor System 的示例代码。

## 目录结构

```
examples/
├── rust/           # Rust 示例
│   ├── ping_pong.rs
│   └── cluster.rs
└── python/         # Python 示例
    ├── ping_pong.py
    ├── cluster.py
    └── README.md
```

## Rust 示例

### Ping-Pong

基本的 Actor 通信示例：

```bash
cargo run --example ping_pong -p pulsing-actor
```

### Cluster

多节点集群通信示例：

```bash
# Terminal 1 - Node 1
cargo run --example cluster -p pulsing-actor -- --node 1

# Terminal 2 - Node 2
cargo run --example cluster -p pulsing-actor -- --node 2
```

## Python 示例

### Ping-Pong

```bash
python examples/python/ping_pong.py
```

### Cluster

```bash
# Terminal 1
python examples/python/cluster.py --port 8000

# Terminal 2
python examples/python/cluster.py --port 8001 --seed 127.0.0.1:8000
```

详细说明请参考 [python/README.md](python/README.md)。

## CLI 快速启动

```bash
# 启动 Router
pulsing actor --type router --http_port 8080 --model_name my-llm

# 启动 Worker
pulsing actor --type transformers --model gpt2 --seeds 127.0.0.1:8000

# 测试
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "my-llm", "messages": [{"role": "user", "content": "Hello"}]}'
```

