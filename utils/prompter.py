import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PromptTool:
    @staticmethod
    def load_prompt(prompt_name: str) -> str:
        """
        加载提示词

        :param path: 提示词文件路径
        :return: 提示词
        """
        try:
            if not prompt_name.endswith(".txt"):
                prompt_name += ".txt"
            plugin_root = Path(__file__).resolve().parent.parent
            prompt_path = plugin_root / "prompts" / prompt_name
            with open(prompt_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"无法找到提示词文件：prompts/{prompt_name}")

    @staticmethod
    def fill(prompt: str, key: str, value: str):
        return prompt.replace(f"[[{key}]]", value)
