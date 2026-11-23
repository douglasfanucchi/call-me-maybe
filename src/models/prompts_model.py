from pydantic import BaseModel, RootModel


class PromptModel(BaseModel):
	prompt: str

class PromptsModel(RootModel[list[PromptModel]]): ...
