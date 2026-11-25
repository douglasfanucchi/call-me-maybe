from llm_sdk import Small_LLM_Model
from .models import FunctionsModel
import numpy as np
from pydantic import BaseModel, InstanceOf


class FunctionNameDetection(BaseModel):
    llm: InstanceOf[Small_LLM_Model]
    functions: FunctionsModel

    def model_post_init(self, _):
        self._functions_descriptions: dict[str, str] = {
            func.name: func.description for func in self.functions.root
        }
        functions_list_str = "\n".join([
            f"{name}: {desc}"
            for name, desc in self._functions_descriptions.items()
        ])
        self._system_message = (
            "<|im_start|>system\n"
            "You are a function router.\n"
            "You have these functions, followed by their descriptions, "
            "that may suit user's needs: \n"
            f"{functions_list_str}\n"
            "The user will give a prompt and it is your job to find the best "
            "function that fits to the user's problem. "
            "You must only answer with the function's name.<|im_end|>\n"
        )

    def generate(self, prompt: str) -> str | None:
        chat = (
            "<|im_start|>user\n"
            f"{prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
            "<think>\n\n</think>\n\n"
        )
        input_ids: list[int] = self.llm.encode(
            self._system_message + chat
        ).flatten().tolist()
        output_ids: list[int] = []
        tokens_count = 0
        next_token = 0
        while tokens_count < 50 and next_token != 151645:
            logits = self.llm.get_logits_from_input_ids(input_ids)
            next_token = int(np.argmax(logits))
            input_ids.append(next_token)
            if next_token != 151645:
                output_ids.append(next_token)
            tokens_count += 1
        result = self.llm.decode(output_ids)
        if result not in self._functions_descriptions.keys():
            return None
        return result
