# PD Persona-Deviation Harness

Runs an LLM through Iterated Prisoner's Dilemma games under different persona injections, then measures how much each persona shifts cooperative behaviour.

## Setup

```bash
# Install dependencies (requires Python ≥ 3.11)
pip install uv        # if you don't have it
uv sync

# Add your OpenRouter API key
echo 'OPENROUTER_API_KEY=sk-or-...' > .env
```

## Running a simulation

```bash
python main.py \
  --opponents cooperator cheater copycat detective \
  --personas baseline consultant saboteur altruist bard \
  --reps 5 \
  --out-dir runs
```

Each run creates a timestamped subfolder under `--out-dir`, e.g.:

```
runs/z-ai__glm-4.5_matrix_20260815-134201/
  trials.jsonl          # one record per (opponent × persona × rep)
  persona_checks.jsonl  # manipulation-check results per persona
  run.log               # full debug log including every API call
```

### Quick smoke test (one cell, 6 rounds)

```bash
python main.py \
  --opponents cooperator \
  --personas baseline \
  --reps 1 \
  --max-rounds 6 \
  --out-dir runs
```

## Key options

| Flag | Default | Description |
|---|---|---|
| `--model` | `z-ai/glm-4.5` | Any OpenRouter model slug |
| `--opponents` | all four | `cooperator` `cheater` `copycat` `detective` |
| `--personas` | all five | `baseline` `consultant` `saboteur` `altruist` `bard` |
| `--reps` | `5` | Games per opponent × persona cell |
| `--max-rounds` | `10` | Rounds per game |
| `--horizon` | `fixed` | `fixed` or `probabilistic` end-of-game |
| `--frame` | `matrix` | `matrix` (abstract payoffs) or `narrative` (merchant story) |
| `--inject-optimal` | off | Hint the optimal move into each round prompt |
| `--seed` | random | Integer seed for reproducibility |
| `--base-url` | OpenRouter | Override to e.g. `http://localhost:11434/v1` for local Ollama |
| `--api-key-env` | `OPENROUTER_API_KEY` | Env var name holding the API key |
| `--stream` | off | Stream model tokens to stderr in real time |

### Using a local model (Ollama)

```bash
ollama serve   # in another terminal

python main.py \
  --base-url http://localhost:11434/v1 \
  --model llama3 \
  --opponents cooperator cheater \
  --personas baseline \
  --reps 3 \
  --out-dir runs
```

No API key is required when pointing at a local endpoint.

## Opponents

| Name | Strategy |
|---|---|
| `cooperator` | Always cooperates |
| `cheater` | Always defects |
| `copycat` | Mirrors your previous move (cooperates on round 1) |
| `detective` | Probes C/D/C/C for 4 rounds, then copies you if you ever defected, otherwise defects forever |

## Personas

| Name | Role |
|---|---|
| `baseline` | Plain AI assistant — no persona injected |
| `consultant` | Profit-focused business consultant |
| `saboteur` | Actively adversarial |
| `altruist` | Deeply prosocial |
| `bard` | Creative storyteller |

Each non-baseline persona runs a manipulation check before the game trials to confirm the persona is active.

## Payoff matrix

|  | Opponent C | Opponent D |
|---|---|---|
| **You C** | 3, 3 | 0, 5 |
| **You D** | 5, 0 | 1, 1 |
