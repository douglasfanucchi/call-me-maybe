*This project has been created as part of the 42 curriculum by dode-lim.*

# Call Me Maybe

## Description

**Call Me Maybe** turns a natural-language request into a structured function call, using a small local language model (`Qwen/Qwen3-0.6B`).

Given a list of function definitions and a list of prompts, the program does not *answer* the prompts. It decides **which function** should be called and **with which arguments**, then writes the result as JSON:

```
"What is the sum of 265 and 345?"
        │
        ▼
{ "prompt": "What is the sum of 265 and 345?",
  "name": "fn_add_numbers",
  "parameters": { "a": 265.0, "b": 345.0 } }
```

A 0.6B-parameter model cannot be trusted to emit well-formed JSON by itself. The goal of the project is therefore **constrained decoding**: the program drives the model token by token and controls what it is allowed to produce, so the output always has the right structure and the right types, whatever the model "wants" to say.

### Overview

| Stage | Module | What it does |
|---|---|---|
| CLI and validation | `src/cli.py`, `src/models/` | Parses flags and validates the two input JSON files with Pydantic |
| Function selection | `src/function_name_detection.py` | Asks the model for the name of the best function and checks it against the known names |
| Argument extraction | `src/params_detection.py` | Builds the JSON of arguments token by token, forcing the structure and masking invalid tokens |
| Orchestration | `src/__main__.py` | Loops over the prompts and writes `data/output/function_calls.json` |
| Model wrapper | `llm_sdk/` | Provided SDK: loads the model and exposes `encode`, `decode` and `get_logits_from_input_ids` |

## Instructions

### Requirements

- Python **3.14** or newer (the code uses nested quotes inside f-strings)
- [`uv`](https://docs.astral.sh/uv/)
- Enough disk space for the model and PyTorch (the first run downloads `Qwen/Qwen3-0.6B` from the Hugging Face Hub)

Dependencies are declared in `pyproject.toml`: `llm-sdk`, `numpy`, `pydantic`, `torch`, `transformers`, `huggingface-hub`, `accelerate`.

### Installation and execution

```bash
make run
```

`make run` installs the dependencies (`make install`) and then runs the program with the default files. The Makefile stores the virtual environment, the `uv` cache and the Hugging Face cache under `~/sgoinfre/call-me-maybe` (the 42 shared storage) instead of your home directory. `make sgoinfre` creates these directories.

| Target | Purpose |
|---|---|
| `make install` | Creates the environment and runs `uv sync` |
| `make run` | Installs, then runs on the default input files |
| `make debug` | Runs `src/__main__.py` under `pdb` |
| `make lint` | `flake8` and `mypy` (the provided `llm_sdk` is excluded) |
| `make lint-strict` | Same, with `mypy --strict` |
| `make clean` | Removes `__pycache__` and `.mypy_cache` directories |

### Command-line flags

The flags use a single dash:

| Flag | Default | Meaning |
|---|---|---|
| `-functions_definition` | `data/input/functions_definition.json` | The functions the model can choose from |
| `-input` | `data/input/function_calling_tests.json` | The prompts to process |
| `-output` | `data/output/function_calls.json` | Where the result is written (parent directories are created) |

### Input formats

`functions_definition.json`: a list of functions, each with a `name`, a `description`, typed `parameters` and a `returns` type.

```json
[
  {
    "name": "fn_add_numbers",
    "description": "Add two numbers together and return their sum.",
    "parameters": { "a": { "type": "number" }, "b": { "type": "number" } },
    "returns": { "type": "number" }
  }
]
```

`function_calling_tests.json`: a list of prompts.

```json
[ { "prompt": "What is the sum of 2 and 3?" } ]
```

Both files are validated with Pydantic (`src/models/`) before the model is loaded. A malformed file stops the program with an error message.

## Example usage

Default files:

```bash
make run
```

Custom files:

```bash
uv run python3 -m src \
    -functions_definition path/to/functions.json \
    -input path/to/prompts.json \
    -output out/result.json
```

Output produced by the program on the provided sample files (excerpt of `data/output/function_calls.json`):

```json
[
  {
    "prompt": "What is the sum of 2 and 3?",
    "name": "fn_add_numbers",
    "parameters": { "a": 2.0, "b": 3.0 }
  },
  {
    "prompt": "Greet john",
    "name": "fn_greet",
    "parameters": { "name": "John" }
  },
  {
    "prompt": "Substitute the word 'cat' with 'dog' in 'The cat sat on the mat with another cat'",
    "name": "fn_substitute_string_with_regex",
    "parameters": {
      "source_string": "The cat sat on the mat with another cat",
      "regex": "cat",
      "replacement": "dog"
    }
  }
]
```

If the model returns a name that is not one of the defined functions, the prompt is skipped and a message is printed to `stderr`; the remaining prompts are still processed.

## Algorithm explanation

An LLM produces, at each step, one **logit per vocabulary token**. Normal generation picks the best token (`argmax`) and appends it. Constrained decoding changes this: before choosing, the program decides which tokens are *legal* at this exact position, sets every other logit to `-inf`, and only then takes the `argmax`. The model keeps full freedom inside the legal set, but it can never leave it.

The prompt is written by hand in ChatML (`<|im_start|>role … <|im_end|>`), which is what Qwen models were trained on. The assistant turn starts with an empty `<think>\n\n</think>\n\n` block, so Qwen3 skips its reasoning phase and its first generated token already belongs to the answer.

### Step 1: choosing the function

`FunctionNameDetection` gives the model a system message listing every function as `name: description`, asks it to answer with the name only, and decodes greedily until the stop token `<|im_end|>` (id `151645`) or 50 tokens. The text is then compared with the known names:

- exact match → the function is selected;
- no match → `None`, and the prompt is skipped.

This step is **validated after generation**, not masked during generation.

### Step 2: extracting the arguments

`ParamsDetection` is created once per selected function. Its system message contains the schema (`{"a": number, "b": number}`). The JSON is then built piece by piece, and the program, not the model, writes everything that is *structure*:

```
{ "a":  <value> , "b":  <value> }
└─┬─┘   └──┬──┘   └─┬─┘
  forced   model    forced
  by code  (masked) by code
```

1. **Structure is forced.** The opening `{`, each key (`"name": `), the separators `, ` and the closing `}` are tokenized by the program and appended to the context. The model never has to generate them, so they can never be wrong, and the key order always follows the function definition.
2. **String values** (`"type": "string"`): the program appends the opening quote, then lets the model generate freely. Each step decodes the chosen token; as soon as it contains a `"`, the text before it is kept, the closing quote is added, and the value ends. A limit of 50 tokens prevents runaway strings.
3. **Number values** (`"type": "number"`): only the tokens that keep the output a valid number are allowed at each step:

   | Output so far | Allowed tokens |
   |---|---|
   | nothing | digits, `-` |
   | `-` | digits |
   | at least one digit, no `.` yet | digits, `.`, `,`, `}` |
   | at least one digit, already a `.` | digits, `,`, `}` |

   The `,` and `}` tokens are *terminators*: when the model picks one, the number is finished and the loop stops. They are only allowed after a digit, so an empty value such as `{"a": , …}` is impossible. The digit set is computed from the model's `vocab.json` (every token that matches `[0-9]+`).
4. After every chosen token, the token is appended to the context before the next forward pass; this is how the model "sees" what it has already written.
5. If a value has no decimal point, `.0` is appended, so numbers are always written as floats (`2.0`).
6. The final string is parsed with `json.loads` in `__main__.py` and written with `json.dumps(indent=2)`.

### Why this guarantees valid output

The structure is written by the program, numbers are generated from a restricted alphabet and string values are closed by the program. The only thing the model decides is *which* digits or characters fill each value.

## Design decisions

- **Hand-driven decoding loop instead of the `generate()` API.** `llm_sdk` exposes raw logits, which is what makes masking possible. The loop is short and each piece (name, string value, number value) is its own method.
- **The program writes the JSON structure; the model only fills values.** This is cheaper and more reliable than asking a 0.6B model to produce `{`, quotes and commas. The model's budget goes entirely to the part that needs understanding.
- **Greedy decoding (`argmax`), no sampling.** Output is deterministic, so a run can be reproduced and debugged.
- **Two separate, small prompts** (route, then extract) instead of one big prompt. The second prompt only contains the schema of the chosen function, which keeps the context short and focused for a small model.
- **ChatML written by hand with an empty think block.** It avoids the model starting with `<think>`, which would break the constrained output.
- **Pydantic everywhere data enters the program.** `FunctionsModel` and `PromptsModel` are `RootModel`s wrapping a list, because both input files have a list at the top level. The `FunctionNameDetection` and `ParamsDetection` classes are also Pydantic models, with `model_post_init` used to build the system message once. The LLM is typed as `InstanceOf[Small_LLM_Model]` because it is not a Pydantic type.
- **Skip, don't crash, when no function matches.** A prompt that cannot be routed is reported on `stderr` and the run continues.
- **Output directory created on demand** with `Path.mkdir(parents=True, exist_ok=True)`, so the program does not depend on `data/output/` existing.
- **Stop token.** `<|im_end|>` is `151645` for the Qwen family; the name-detection loop stops on that id (hard-coded, so a different model family would need a different value).

## Performance analysis

Measured on the 11 provided prompts and 5 provided functions, one run, WSL2 (Linux 6.18), `Qwen/Qwen3-0.6B` with the device chosen automatically by `llm_sdk`:

**Speed.** `make run` took about **1 min 40 s** of wall-clock time, including model loading and the dependency check, i.e. roughly 9 s per prompt. Each token needs a full forward pass over the whole sequence: `llm_sdk` does not expose a KV cache, so the context is recomputed at every step. Number masking also scans the vocabulary (about 150k entries) with a regex every time a number is generated. Both are the main costs and the main candidates for optimization.

**Reliability.** Every output file produced was valid JSON that matches the function schema (right keys, in order, with numbers as numbers and strings as strings), because the structure is not left to the model. Decoding is greedy, so the same input produces the same output.

**Accuracy** (checked by hand against the expected behaviour):

| Measure | Result |
|---|---|
| Correct function chosen | **11 / 11** |
| Arguments semantically correct | **8 / 11** if changing the case of a name is accepted; **6 / 11** if the value must be copied exactly |

Arguments that were wrong or questionable:

| Prompt | Got | Problem |
|---|---|---|
| `Greet shrek` / `Greet john` | `"Shrek"` / `"John"` | The model capitalised the name. Probably acceptable, but not a verbatim copy. |
| `Reverse the string 'hello'` | `"olleh"` | The model performed the operation instead of extracting the argument; it should be `"hello"`. |
| `Replace all numbers in "Hello 34 I'm 233 years old" with NUMBERS` | `([0-9]+) ([0-9]+) ([0-9]+)` | Wrong regex; `[0-9]+` was expected. |
| `Replace all vowels in 'Programming is fun' with asterisks` | replacement `"*****"` | The regex is right, the replacement should be a single `*`. |

The constraint guarantees that the *shape* is right. Whether the *content* is right still depends on the 0.6B model and on the prompt, which is where the remaining errors come from.

## Challenges faced

- **Tokens are not characters.** The first versions of the string and number loops compared whole tokens against `,` or `}`. The tokenizer can return a token that contains a quote plus other characters, so the end of a value was missed or extra characters were kept. For strings, the fix was to decode the token and cut it at the first `"`, adding the closing quote back. For numbers, the fix was to mask the logits so only valid tokens are possible (and to stop on the terminator tokens).
- **The model never saw its own output.** The chosen token was added to the output list but not to `input_ids`, so every `argmax` ran on the same context and returned the same token again. Appending to `input_ids` inside the loop fixed it.
- **List aliasing.** Once the loops appended to `input_ids`, the caller's list was modified too, and the value was inserted twice in the context. Each value function now starts with `input_ids = list(input_ids)`.
- **A wrong variable in the loop.** A leftover `next` (the Python builtin) was appended instead of `next_token_id`, which made `torch.tensor` fail with `'builtin_function_or_method' object cannot be interpreted as an integer`.
- **Empty or invalid numbers.** If the terminator tokens are allowed from the first step, the model can close the value without writing a digit. Terminators are only allowed once at least one digit exists, and `-` only as the first character.
- **Qwen3 starts by thinking.** Without the empty `<think>` block, the first generated token would be `<think>`, which collides with the constraints. The block is part of the prompt.
- **Pydantic with a non-Pydantic type.** The LLM object is not a Pydantic type, so the models use `InstanceOf[...]`, and the custom `__init__` was replaced by `model_post_init`.

## Testing strategy

There is no automated test suite yet. The implementation was validated in the following ways:

- **End-to-end runs** on the provided `function_calling_tests.json` and `functions_definition.json`. The output was read by hand and compared with the expected behaviour (see the Accuracy table above).
- **Input validation.** Pydantic rejects malformed or incorrectly shaped input files before the model is loaded.
- **Incremental debugging of the decoding loops**, printing the produced JSON per prompt. This is how the problems listed in "Challenges faced" were found.
- **Static checks** with `make lint` (`flake8` and `mypy`), which currently pass with no issues. All modules, classes and functions in `src/` have Google-style docstrings (PEP 257).

Natural next steps: unit tests for the number mask (every prefix → allowed set), for the string terminator logic with tokens like `",` or `hello"`, and a test that checks that every output file matches its function's schema.    

## Resources

### References

- Willard, B. & Louf, R., *Efficient Guided Generation for Large Language Models* (2023): https://arxiv.org/abs/2307.09702
- Qwen Team, *Qwen3 Technical Report* (2025): https://arxiv.org/abs/2505.09388
- Qwen3-0.6B model card (chat template, `<think>` behaviour): https://huggingface.co/Qwen/Qwen3-0.6B
- Hugging Face Transformers documentation (tokenizers, special tokens, chat templates): https://huggingface.co/docs/transformers
- Pydantic documentation (models, `RootModel`, `model_validate_json`, `TypeAdapter`): https://docs.pydantic.dev/latest/
- Python `argparse` documentation: https://docs.python.org/3/library/argparse.html
- JSON specification (value grammar used to decide where a value ends): https://www.json.org/
- `uv` documentation: https://docs.astral.sh/uv/

### How AI was used

I used Claude (Claude Code) as an assistant during the project. The design of the decoding approach and the final code are mine; AI was used for explanations, for reviewing code and for this document:

- **Concepts and syntax questions:** how to detect the end of a JSON value; how Pydantic works (`BaseModel`, validators, `extra="forbid"`, `RootModel` versus `TypeAdapter`, validating a JSON file); how `argparse` and its `Namespace` work; multi-line string concatenation; inverting a dictionary; getting the `argmax` of the logits.
- **Model-specific details:** the ChatML special tokens, how to look up their ids through the tokenizer, and how to stop Qwen3 from thinking with an empty `<think>` block.
- **Debugging:** reading the traceback caused by the `next` builtin, the missing `accelerate` dependency, and a review of `params_detection.py` that pointed out the aliasing of `input_ids`, the token-level end-of-value detection, and the missing closing quote. The review also suggested masking the logits for numbers; I wrote and adapted the final implementation myself.
- **Documentation:** this README was drafted by Claude from the source code and from our conversations, and the accuracy and timing figures come from a real run of the program.
