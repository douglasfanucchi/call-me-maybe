"""Pydantic models for the functions definition file."""

from pydantic import BaseModel, RootModel


class TypeModel(BaseModel):
    """Type of a function parameter or of a return value.

    Attributes:
        type: Name of the type as written in the definition file, for
            example ``"string"`` or ``"number"``.
    """

    type: str


class FunctionModel(BaseModel):
    """Definition of a function the model can choose to call.

    Attributes:
        name: Unique name of the function.
        description: Short text that explains what the function does.
            It is shown to the language model to help it choose.
        parameters: Parameter names mapped to their types, in the order
            they must appear in the generated JSON.
        returns: Type of the value returned by the function.
    """

    name: str
    description: str
    parameters: dict[str, TypeModel]
    returns: TypeModel


class FunctionsModel(RootModel[list[FunctionModel]]):
    """List of function definitions.

    It validates a JSON file whose top level is an array. The validated
    list is available in the ``root`` attribute.
    """

    ...
