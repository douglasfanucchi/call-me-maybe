from argparse import ArgumentParser
from typing import Any


def parse_args() -> dict[str, Any]:
    parser = ArgumentParser(prog="Call Me Maybe")
    parser.add_argument(
        "-functions_definition",
        default="data/input/functions_definition.json"
    )
    parser.add_argument(
        "-input",
        default="data/input/function_calling_tests.json"
    )
    parser.add_argument(
        "-output",
        default="data/output/function_calls.json"
    )
    namespace = parser.parse_args()
    return vars(namespace)
