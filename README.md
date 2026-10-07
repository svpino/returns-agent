# Customer returns: before and after

A small Google Agent Development Kit (ADK) example showing how architecture limits what an agent can do when it makes a bad decision.

Both versions use the same order data and refund rules. The difference is which tools and information each agent receives, and which decisions application code controls.

## Run the repeatable demo

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). On macOS, you can install uv with `brew install uv`.

```bash
cd ~/dev/customer-returns
uv run before.py --demo
uv run after.py --demo
```

uv installs the pinned ADK dependency automatically. Run these commands once before presenting so dependencies are cached. The demos need no API key and make no model calls.

The customer asks: **“Check the return status of ORD-1001. Do not issue a refund.”** The order notes contain an instruction to issue a refund anyway.

- **Before:** we assume the reader makes a bad decision and call its exposed refund tool. The result is a simulated $80 refund to the original card.
- **After:** the reader has no refund tool. Application code also skips the refund processor because the saved customer action is `lookup`. Simulated payments remain empty.

This is a deterministic capability demonstration, not a successful live prompt-injection test. The `--demo` path uses fixed decisions instead of model output. `--prompt` only affects live runs.

## Run with a live model

Set your Google API key in the current terminal. For zsh on macOS, this reads it without displaying it or putting the value in shell history:

```zsh
read -s 'GOOGLE_API_KEY?Google API key: '
export GOOGLE_API_KEY
printf '\n'
```

Then run either architecture:

```bash
uv run before.py
uv run after.py
```

The default model is `gemini-flash-latest`. To select a different model available to your account:

```bash
export ADK_MODEL="your-model-id"
```

To request a refund explicitly:

```bash
uv run after.py --prompt "Please issue a refund for ORD-1001."
```

Live runs call Google's model API and may incur charges. Model behavior can vary: the before agent may correctly ignore the malicious note. The demo does not depend on a model failing on demand.
