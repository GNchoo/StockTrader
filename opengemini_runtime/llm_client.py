import json
import os
import re
import subprocess
from json import JSONDecoder
from openai import OpenAI


SYSTEM_PROMPT = """
너는 OpenGemini 기반 에이전트다.
반드시 JSON 객체 **하나만** 출력하라. 그 외 텍스트/설명/코드블록 금지.
허용 포맷:
1) {"type":"reply","text":"..."}
2) {"type":"tool","tool":"list_dir|read_file|write_file|edit_replace|memory_add|memory_search","args":{...}}
""".strip()


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gemini-2.5-flash")
        self.gemini_bin = os.getenv("GEMINI_BIN", "/home/linuxbrew/.linuxbrew/bin/gemini")

        self.client = None
        if self.base_url and self.api_key:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _extract_action_json(self, text: str):
        # 1) 전체가 JSON이면 바로 사용
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and obj.get("type") in {"reply", "tool"}:
                return obj
        except Exception:
            pass

        # 2) 텍스트 중 JSON 객체 후보를 모두 탐색해서 마지막 유효 action 채택
        dec = JSONDecoder()
        candidates = []
        for i, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                obj, end = dec.raw_decode(text[i:])
                if isinstance(obj, dict) and obj.get("type") in {"reply", "tool"}:
                    candidates.append(obj)
            except Exception:
                continue

        if candidates:
            return candidates[-1]

        return None

    def _decide_via_gemini_cli(self, messages):
        convo = "\n".join([f"[{m['role']}] {m['content']}" for m in messages])
        prompt = f"{SYSTEM_PROMPT}\n\n대화:\n{convo}\n\nJSON 객체 하나만 출력." 
        proc = subprocess.run(
            [self.gemini_bin, "-m", self.model, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()

        if proc.returncode != 0:
            return {"type": "reply", "text": f"Gemini CLI 오류: {(err or out)[:500]}"}

        action = self._extract_action_json(out)
        if action is not None:
            return action

        return {"type": "reply", "text": "응답 파싱 실패: JSON action을 찾지 못했습니다."}

    def set_model(self, model: str):
        self.model = model

    def get_model(self) -> str:
        return self.model

    def decide(self, messages):
        if self.client is None:
            return self._decide_via_gemini_cli(messages)

        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
