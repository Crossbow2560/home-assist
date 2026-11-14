#!/usr/bin/env bash
# Start llama.cpp's OpenAI-compatible server with the local Qwen model.
MODEL="${MODEL:-$HOME/Models/Qwen3.5-0.8B-UD-Q4_K_XL.gguf}"
LLAMA_DIR="${LLAMA_DIR:-$HOME/llama-cpp}"
export LD_LIBRARY_PATH="$LLAMA_DIR/lib:$LD_LIBRARY_PATH"
exec "$LLAMA_DIR/bin/llama-server" -m "$MODEL" --host 127.0.0.1 --port 8080 -ngl 99 -c 8192 --jinja "$@"
