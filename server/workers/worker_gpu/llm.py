import logging
from typing import Callable
from enum import Enum
from llama_cpp import Llama


from workers.worker_gpu.challenge import Challenge
from workers.worker_gpu.plugins.base import PluginBase

class LlmResponseEnum(Enum):
    OK = 1
    CLAWEDBACK = 2
    CANCELLED = 3

class LlmWrapper:
    def __init__(self):
        self.__llm = None
        self.__complete_message = ""
        self.__logger = logging.getLogger(__name__)

    def setup(self):
        self.__llm = Llama(model_path="./llama-2-7b-chat.Q5_K_M.gguf", n_gpu_layers=-1, chat_format="llama-2", n_ctx=1024, n_batch=1024)
    
    def discuss(self, socket_id:str, challenge: Challenge, user_message: str, token_handler: Callable[[str], bool], plugins: list[PluginBase]) -> LlmResponseEnum:
        """
        Dicuss with the LLM

        Returns:
        The state of the LLM
        """
        self.__complete_message = ""
        clawback_enabled = challenge.clawback_enabled
        self.__logger.info("[%s] [Challenge-%d] User message: %s", socket_id, challenge.id, user_message)
        stream = self.__llm.create_chat_completion(
            messages=[
                {"role":"system", "content": challenge.metaprompt},
                {"role": "user", "content": user_message}
            ],
            stream=True
        )
        for output in stream:
            if "content" in output["choices"][0]["delta"].keys():
                token = output["choices"][0]["delta"]["content"]
                self.__complete_message += token
                if clawback_enabled:
                    should_clawback = challenge.clawback(self.__complete_message)
                    if should_clawback:
                        self.__logger.info("[%s] [Challenge-%d] LLM Message: %s [CLAWEDBACK]", socket_id, challenge.id, self.__complete_message)
                        return LlmResponseEnum.CLAWEDBACK
                    
                if not token_handler(token):
                    # Cancel launched
                    self.__logger.info("[%s] [Challenge-%d] LLM Message: %s [CANCELLED]", socket_id, challenge.id, self.__complete_message)
                    return LlmResponseEnum.CANCELLED
                
        for plugin in plugins:
            plugin.execute(self.__complete_message)
        self.__logger.info("[%s] [Challenge-%d] LLM Message: %s [OK]", socket_id, challenge.id, self.__complete_message)
        return LlmResponseEnum.OK
    