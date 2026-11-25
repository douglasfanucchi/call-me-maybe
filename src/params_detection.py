from pydantic import BaseModel, InstanceOf
from llm_sdk import Small_LLM_Model
from .models import FunctionModel, TypeModel
import numpy as np
import json
import regex
import math


class ParamsDetection(BaseModel):
    llm: InstanceOf[Small_LLM_Model]
    function: FunctionModel

    def model_post_init(self, _):
        self._system_message = (
            "<|im_start|>system\n"
            "You extract information from a sentence and "
            "answer ONLY with a JSON object.\n"
            "Schema:\n"
            f" \n{self.generate_default_structure(self.function.parameters)}\n"
            "Use null when information is missing. No extra text.<|im_end|>"
        )

    def generate_default_structure(
        self,
        parameters: dict[str, TypeModel]
    ) -> str:
        result = [
            f'"{key}": {value_type.type}'
            for key, value_type in parameters.items()
        ]
        return f"{{{", ".join(result)}}}"

    def generate(self, prompt: str) -> str:
        user_prompt = (
            "<|im_start|>user\n"
            f"{prompt}<|im_end|>"
        )
        if len(self.function.parameters.items()) == 0:
            return "{}"
        input_ids = self.llm.encode((
            f"{user_prompt}"
            "<|im_start|>assistant\n"
            "<think>\n\n</think>\n\n"
        )).flatten().tolist()
        output_ids: list[int] = []
        with open(self.llm.get_path_to_vocab_file()) as file:
            vocab: dict[str, int] = json.load(file)
        items = 0
        for parameter, type in self.function.parameters.items():
            json_key_tokens_ids = self.llm.encode((
                f"{"{" if items == 0 else ", "}"
                f'"{parameter}": {'"' if type.type == "string" else ""}'
            )).flatten().tolist()
            input_ids = input_ids + json_key_tokens_ids
            output_ids = output_ids + json_key_tokens_ids
            if type.type == "string":
                json_value_tokens_ids = self.generate_json_string_value(
                    input_ids
                )
            elif type.type == "number":
                json_value_tokens_ids = self.generate_json_number_value(
                    input_ids,
                    vocab
                )
            input_ids = input_ids + json_value_tokens_ids
            output_ids = output_ids + json_value_tokens_ids
            items += 1
        output_ids.append(vocab["}"])
        return self.llm.decode(output_ids)

    def generate_json_string_value(self, input_ids: list[int]) -> list[int]:
        input_ids = list(input_ids)
        token_count = 0
        output_ids: list[int] = []

        while token_count < 50:
            logits = self.llm.get_logits_from_input_ids(input_ids)
            next_token_id = int(np.argmax(logits))
            token = self.llm.decode(next_token_id)
            if '"' in token:
                output_ids = output_ids + self.llm.encode(
                    token[0:token.find('"') + 1]
                ).flatten().tolist()
                break
            output_ids.append(next_token_id)
            input_ids.append(next_token_id)
            token_count += 1
        return output_ids
    
    def generate_json_number_value(self, input_ids: list[int], vocab) -> list[int]:
        input_ids = list(input_ids)
        output_ids: list[int] = []
        digit_ids = {i for t, i in vocab.items() if regex.fullmatch(r"[0-9]+", t)}
        minus, dot = vocab["-"], vocab["."]
        terminators = {vocab[","], vocab["}"]}
        has_digit = has_dot = False

        for _ in range(50):
            allowed = set(digit_ids)
            if not output_ids:
                allowed.add(minus)
            if has_digit and not has_dot:
                allowed.add(dot)
            if has_digit:
                allowed |= terminators

            logits = np.asarray(self.llm.get_logits_from_input_ids(input_ids))
            mask = np.full(len(logits), -np.inf)
            mask[list(allowed)] = 0
            next_id = int(np.argmax(logits + mask))

            if next_id in terminators:
                break
            has_digit |= next_id in digit_ids
            has_dot |= next_id == dot
            output_ids.append(next_id)
            input_ids.append(next_id)
        if not has_dot:
            output_ids.append(vocab["."])
            output_ids.append(vocab["0"])
        return output_ids
