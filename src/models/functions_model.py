from pydantic import BaseModel, RootModel


class TypeModel(BaseModel):
    type: str


class FunctionModel(BaseModel):
    name: str
    description: str
    parameters: dict[str, TypeModel]
    returns: TypeModel


class FunctionsModel(RootModel[list[FunctionModel]]):
    ...
