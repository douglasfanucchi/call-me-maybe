"""Command-line interface of the function calling tool."""

from argparse import ArgumentParser
from typing import Any


def parse_args() -> dict[str, Any]:
    """Parse the command-line arguments of the program.

    The flags use a single dash (for example ``-input file.json``).
    Every flag is optional and falls back to a default path.

    Returns:
        A dictionary with the following keys:

        * ``functions_definition``: path to the JSON file that describes
          the available functions.
        * ``input``: path to the JSON file that holds the prompts.
        * ``output``: path to the JSON file where the result is written.

    Raises:
        SystemExit: If an unknown flag is given or a flag has no value
            (raised by ``argparse``, with exit code 2).
    """
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
