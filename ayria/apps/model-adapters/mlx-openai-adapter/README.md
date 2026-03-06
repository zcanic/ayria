# MLX OpenAI Adapter

This folder is reserved for a small service that exposes MLX-backed models
through an OpenAI-compatible API.

Why this exists:
- the runtime should not care whether a local model comes from Ollama or MLX
- a normalized HTTP interface reduces orchestration complexity
- Apple Silicon support can evolve independently from runtime logic
