from .cli import parse_args
from .models import FunctionsModel, PromptsModel
from pathlib import Path

args = parse_args()

try:
    functions = FunctionsModel.model_validate_json(
        Path(args["functions_definition"]).read_text()
    )

    prompts = PromptsModel.model_validate_json(
        Path(args["input"]).read_text()
    )
except Exception as e:
    print(f"Error: {e}")
