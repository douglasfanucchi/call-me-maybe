"""Entry point: turn prompts into function calls.

Run with ``python -m src``. For every prompt of the input file, the
program picks the best function, extracts its arguments with constrained
decoding and writes all the results to the output file as JSON.

Prompts for which no function is found are reported on ``stderr`` and
skipped. Any other error is printed and nothing is written.
"""

from .cli import parse_args
from .models import FunctionsModel, PromptsModel
from pathlib import Path
from llm_sdk import Small_LLM_Model
from .function_name_detection import FunctionNameDetection
from .params_detection import ParamsDetection
import sys
import json

try:
    args = parse_args()

    functions = FunctionsModel.model_validate_json(
        Path(args["functions_definition"]).read_text()
    )

    prompts = PromptsModel.model_validate_json(
        Path(args["input"]).read_text()
    )

    result: list[dict] = []
    llm = Small_LLM_Model()
    function_detection = FunctionNameDetection(
        llm=llm,
        functions=functions
    )
    for prompt in prompts.root:
        function_name = function_detection.generate(prompt.prompt)
        if function_name is None:
            print(
                "There is no function to solve the following prompt: "
                f"{prompt.prompt}",
                file=sys.stderr
            )
            continue
        func = next(filter(
            lambda func: func.name == function_name, functions.root)
        )
        params = ParamsDetection(
            llm=llm,
            function=func
        )
        result.append({
            "prompt": prompt.prompt,
            "name": function_name,
            "parameters": json.loads(params.generate(prompt.prompt))
        })
    output_file = Path(args["output"])
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    output_file.write_text(json.dumps(result, indent=2) + "\n")
except Exception as e:
    print(f"Error: {e}")
