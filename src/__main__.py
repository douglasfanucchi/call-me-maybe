from .cli import parse_args
from .models import FunctionsModel, PromptsModel
from pathlib import Path

args = parse_args()

function = FunctionsModel.model_validate_json(
    Path(args["functions_definition"]).read_text()
)

prompts = PromptsModel.model_validate_json(
    Path(args["input"]).read_text()
)

print(function.root[0].name)
