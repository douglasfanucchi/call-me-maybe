"""Choice of the function that best fits a prompt."""

from llm_sdk import Small_LLM_Model
from .models import FunctionsModel
import numpy as np
from pydantic import BaseModel, InstanceOf
from typing import Any


class FunctionNameDetection(BaseModel):
    """Select, with a language model, the function that solves a prompt.

    The model receives the name and description of every function and is
    asked to answer with a function name only. The answer is accepted
    only if it is the exact name of a known function.

    Attributes:
        llm: The language model used for the generation.
        functions: The functions the model can choose from.
    """

    llm: InstanceOf[Small_LLM_Model]
    functions: FunctionsModel

    def model_post_init(self, _: Any) -> None:
        """Build the system message once the fields are validated.

        Called by Pydantic after ``__init__``. It creates the private
        attributes ``_functions_descriptions`` (function name mapped to
        its description) and ``_system_message`` (the ChatML system
        turn that lists every function).

        Args:
            _: Validation context given by Pydantic. It is not used.
        """
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
        """Find the function that best fits a prompt.

        The tokens are chosen greedily (highest logit) until the model
        emits the ``<|im_end|>`` token (id 151645) or 50 tokens have
        been produced. The generated text is then checked against the
        names of the known functions.

        Args:
            prompt: The natural-language request of the user.

        Returns:
            The name of the selected function, or ``None`` if the text
            produced by the model is not the name of a known function.
        """
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
        return str(result)
