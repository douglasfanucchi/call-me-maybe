from llm_sdk import Small_LLM_Model
import json
import numpy as np
import sys
import re

decoder = json.decoder.JSONDecoder()
model = Small_LLM_Model()

functions: list[dict] = [
    {
        "name": "fn_add_numbers",
        "description": "Add two numbers together and return their sum.",
        "parameters": {
        "a": {
            "type": "number"
        },
        "b": {
            "type": "number"
        }
        },
        "returns": {
        "type": "number"
        }
    },
    {
        "name": "fn_greet",
        "description": "Generate a greeting message for a person by name.",
        "parameters": {
        "name": {
            "type": "string"
        }
        },
        "returns": {
        "type": "string"
        }
    },
    {
        "name": "fn_reverse_string",
        "description": "Reverse a string and return the reversed result.",
        "parameters": {
        "s": {
            "type": "string"
        }
        },
        "returns": {
        "type": "string"
        }
    },
    {
        "name": "fn_get_square_root",
        "description": "Calculate the square root of a number.",
        "parameters": {
        "a": {
            "type": "number"
        }
        },
        "returns": {
        "type": "number"
        }
    },
    {
        "name": "fn_substitute_string_with_regex",
        "description": "Replace all occurrences matching a regex pattern in a string.",
        "parameters": {
            "source_string": {
                "type": "string"
            },
            "regex": {
                "type": "string"
            },
            "replacement": {
                "type": "string"
            }
            },
        "returns": {
            "type": "string"
        }
    },
    {
        "name": "fn_does_not_get_usa_president",
        "description": "It does not returns the name of USA president",
        "parameters": {}
    },
    {
        "name": "fn_get_usa_president",
        "description": "It returns the name of USA president",
        "parameters": {}
    }
]

functions_summary: list[dict] = [
    ({
        "name": _function["name"],
        "description": _function["description"]
    })
    for _function in functions
]

inputs = [
  {
    "prompt": "What is the sum of 2 and 3?"
  },
  {
    "prompt": "What is the sum of 265 and 345?"
  },
  {
    "prompt": "Greet shrek"
  },
  {
    "prompt": "Greet john"
  },
  {
    "prompt": "Reverse the string 'hello'"
  },
  {
    "prompt": "Reverse the string 'world'"
  },
  {
    "prompt": "What is the square root of 16?"
  },
  {
    "prompt": "Calculate the square root of 144"
  },
  {
    "prompt": "Replace all numbers in \"Hello 34 I'm 233 years old\" with NUMBERS"
  },
  {
    "prompt": "Replace all vowels in 'Programming is fun' with asterisks"
  },
  {
    "prompt": "Substitute the word 'cat' with 'dog' in 'The cat sat on the mat with another cat'"
  },
  {
    "prompt": "Who is the President of USA?"
  }
]

raw_inputs = [
    input["prompt"] for input in inputs
]

for input in raw_inputs:
    prompt = "I have a list of functions that are in JSON format. "
    prompt += "The functions format are: "
    prompt += '{"name": "function name", "description": "function description"}\n'
    prompt += "Each function has a name specified in the \"name\" field "
    prompt += "and perform some task. The task that it performs is specified in "
    prompt += '"description" field.\n'
    prompt += "Given the following prompt, you must output the function NAME "
    prompt += "that is most suited for the task.\n"
    prompt += "Output format must be: "
    prompt += '{"name": "name of the function that is most suited to the task"}\n'
    prompt += f"Available functions:\n{str(functions_summary).replace("'", '"')}\n"
    prompt += f"Prompt: {input}\n"
    prompt += 'Output: {"name": "'

    matched: re.Match | None = None
    while matched is None:
        token_ids = model.encode(prompt)
        logits = np.array(
            model.get_logits_from_input_ids(token_ids.tolist()[0])
        )
        token_id = int(np.argmax(logits))
        token_decoded = model.decode(token_id)
        prompt += token_decoded
        matched = re.search('Output: {"name": "(?P<name>[A-z_0-9]{1,})"', prompt)
    function_name = matched.group("name")
    sys.stdout.write(f"{input}: {matched.group("name")}\n")
    _function = next(
        filter(lambda item: item["name"] == function_name, functions)
    )
    prompt = f"Given the function {_function["name"]} "
