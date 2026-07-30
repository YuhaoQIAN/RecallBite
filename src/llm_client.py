"""LLM client abstraction for RecallBite.

Supports pluggable model providers.
Falls back to deterministic demo mode when no API key is configured.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from src.prompts import ACTIVATION_SYSTEM, MATERIAL_ANALYSIS_SYSTEM


class LLMClient(ABC):
    """Abstract LLM client for material analysis and memory activation."""

    @abstractmethod
    def analyze_material(self, material: dict, output_schema: dict, output_language: str = "auto") -> dict:
        """Analyze a material document and return structured insights."""
        ...

    @abstractmethod
    def activate_memory(
        self,
        task: dict,
        cards: list[dict],
        output_schema: dict,
    ) -> dict:
        """Activate recalled cards into ready-to-use content for the current task."""
        ...

    @property
    @abstractmethod
    def mode_label(self) -> str:
        """Human-readable label for the current mode (e.g. 'AI analysis', 'Demo fallback')."""
        ...


class DeterministicLLMClient(LLMClient):
    """Fallback client that uses deterministic rule-based analysis.

    No external API calls. All logic is local.
    """

    @property
    def mode_label(self) -> str:
        return "Demo fallback mode (deterministic rules)"

    def analyze_material(self, material: dict, output_schema: dict, output_language: str = "auto") -> dict:
        """Placeholder: actual logic lives in analyzers/material_analyzer.py."""
        # The deterministic analyzer is called directly from generator.py
        # This method exists only for interface completeness.
        raise NotImplementedError("Use analyzers.material_analyzer directly in demo mode")

    def activate_memory(self, task: dict, cards: list[dict], output_schema: dict) -> dict:
        """Placeholder: actual logic lives in analyzers/activation_analyzer.py."""
        raise NotImplementedError("Use analyzers.activation_analyzer directly in demo mode")


class OpenAILLMClient(LLMClient):
    """OpenAI-compatible API client (supports DeepSeek, Qwen, Azure, Ollama, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client: Any | None = None

    @property
    def provider_name(self) -> str:
        """Derive a readable provider name from base_url."""
        url = self.base_url.lower()
        if "deepseek" in url:
            return "DeepSeek"
        if "openai" in url and "azure" not in url:
            return "OpenAI"
        if "azure" in url:
            return "Azure OpenAI"
        if "qwen" in url or "aliyun" in url or "dashscope" in url:
            return "Qwen"
        if "ollama" in url or ":11434" in url:
            return "Ollama"
        # Fallback to netloc
        from urllib.parse import urlparse
        netloc = urlparse(self.base_url).netloc
        return netloc.split(":")[0]

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI
            import httpx
            skip_verify = os.getenv("RECALLBITE_LLM_SKIP_SSL_VERIFY", "").lower() in ("1", "true", "yes")
            proxy = os.getenv("RECALLBITE_HTTP_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

            client_kwargs: dict[str, Any] = {}
            if skip_verify or proxy:
                http_kwargs: dict[str, Any] = {}
                if skip_verify:
                    http_kwargs["verify"] = False
                if proxy:
                    http_kwargs["proxy"] = proxy
                client_kwargs["http_client"] = httpx.Client(**http_kwargs)

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, **client_kwargs)
        return self._client

    @property
    def mode_label(self) -> str:
        return f"AI analysis mode ({self.provider_name} / {self.model})"

    def _call_chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=4000,
        )
        return response.choices[0].message.content or ""

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from markdown code blocks or raw text."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # Remove first and last code fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)

    @staticmethod
    def _chunk_text(text: str, max_size: int = 6000) -> list[tuple[str, str]]:
        """Split text into chunks with location hints.

        Returns list of (chunk_text, location_hint).
        """
        import re
        paragraphs = re.split(r"\n\s*\n", text.strip())
        chunks: list[tuple[str, str]] = []
        current_location = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            loc_match = re.search(r"\[(Page|Slide)\s*\d+\]", para)
            if loc_match:
                current_location = loc_match.group(0)
            if len(para) <= max_size:
                chunks.append((para, current_location))
            else:
                sentences = re.split(r"(?<=[。！？.!?])\s+", para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_size:
                        current_chunk = (current_chunk + " " + sent).strip() if current_chunk else sent
                    else:
                        if current_chunk:
                            chunks.append((current_chunk, current_location))
                        current_chunk = sent
                if current_chunk:
                    chunks.append((current_chunk, current_location))
        return chunks

    @staticmethod
    def _merge_chunk_results(results: list[dict]) -> dict:
        """Merge analysis results from multiple chunks."""
        merged: dict[str, Any] = {
            "thirty_second_takeaway": "",
            "key_insights": [],
            "use_scenarios": [],
            "talking_points": [],
            "questions_to_ask": [],
            "memory_hook": "",
            "evidence_spans": [],
            "topic_label": "",
        }
        seen_insights: set[str] = set()
        seen_spans: set[str] = set()

        for r in results:
            if not merged["thirty_second_takeaway"]:
                merged["thirty_second_takeaway"] = r.get("thirty_second_takeaway", "")
            if not merged["topic_label"]:
                merged["topic_label"] = r.get("topic_label", "")
            if not merged["memory_hook"]:
                merged["memory_hook"] = r.get("memory_hook", "")

            for item in r.get("key_insights", []):
                text_key = item.get("insight", "")[:80]
                if text_key and text_key not in seen_insights:
                    seen_insights.add(text_key)
                    merged["key_insights"].append(item)

            for span in r.get("evidence_spans", []):
                text_key = span.get("text", "")[:80]
                if text_key and text_key not in seen_spans:
                    seen_spans.add(text_key)
                    merged["evidence_spans"].append(span)

            merged["use_scenarios"].extend(r.get("use_scenarios", []))
            merged["talking_points"].extend(r.get("talking_points", []))
            merged["questions_to_ask"].extend(r.get("questions_to_ask", []))

        # Deduplicate lists while preserving order
        for key in ["use_scenarios", "talking_points", "questions_to_ask"]:
            seen: set[str] = set()
            unique: list[str] = []
            for item in merged[key]:
                item_str = str(item)
                if item_str not in seen:
                    seen.add(item_str)
                    unique.append(item)
            merged[key] = unique

        return merged

    def analyze_material(self, material: dict, output_schema: dict, output_language: str = "auto") -> dict:
        """Call DeepSeek to analyze material and return structured insights.

        Long materials are split into chunks, analyzed individually, then merged.
        output_language: auto, zh, en, or bilingual.
        """
        text = material.get("text", "")
        if not text:
            raise ValueError("Empty material")

        chunks = self._chunk_text(text, max_size=6000)
        if not chunks:
            raise ValueError("No valid chunks")

        # For short texts, analyze in one call
        if len(chunks) == 1:
            chunk_text, location = chunks[0]
            return self._analyze_single_chunk(chunk_text, location, output_language)

        # For long texts, analyze each chunk and merge (max 5 chunks to limit API cost)
        results: list[dict] = []
        for idx, (chunk_text, location) in enumerate(chunks[:5], 1):
            try:
                result = self._analyze_single_chunk(chunk_text, location, output_language)
                results.append(result)
            except Exception:
                # Skip failed chunks; others still contribute
                continue

        if not results:
            raise ValueError("All chunk analyses failed")

        return self._merge_chunk_results(results)

    def _analyze_single_chunk(self, text: str, location: str = "", output_language: str = "auto") -> dict:
        """Analyze a single chunk of material."""
        loc_hint = f"Location: {location}\n" if location else ""
        
        # Language instruction
        lang_instructions = {
            "zh": "\nIMPORTANT: Write ALL insights, takeaways, talking points, and questions in natural Chinese (中文). Keep evidence spans in their original language.",
            "en": "\nIMPORTANT: Write ALL insights, takeaways, talking points, and questions in natural English.",
            "bilingual": "\nIMPORTANT: For each insight, provide BOTH a Chinese version and an English version. Format: '中文内容 / English content'. Keep evidence spans in their original language.",
        }
        lang_hint = lang_instructions.get(output_language, "")
        
        user_prompt = f"""Analyze the following material and return valid JSON.

{loc_hint}Material:
---
{text}
---

Return JSON with this structure:
{{
  "thirty_second_takeaway": "One sentence capturing the core value.",
  "key_insights": [
    {{
      "insight": "The insight text.",
      "why_it_matters": "Why this matters professionally.",
      "evidence": "Exact quote or paraphrase from the source.",
      "location": ""
    }}
  ],
  "use_scenarios": ["Proposal / Report: ...", "Meeting / Discussion: ...", "CPD / Sharing: ..."],
  "talking_points": ["...", "..."],
  "questions_to_ask": ["...", "...", "..."],
  "memory_hook": "Short memorable phrase.",
  "evidence_spans": [
    {{"text": "Exact evidence text.", "location": ""}}
  ],
  "topic_label": "Short topic label."
}}

Rules:
- IGNORE welcome, thank-yous, speaker intros, agendas, disclaimers.
- PRIORITIZE numbers, percentages, regulatory changes, causal claims, risks, opportunities.
- Do NOT invent facts not in the material.
- Do NOT use organization names (e.g. American Heart Association), copyright notices, URLs, or page numbers as insights or topic labels.
- Output ONLY valid JSON, no extra text.
{lang_hint}
"""

        content = self._call_chat(MATERIAL_ANALYSIS_SYSTEM, user_prompt)
        result = self._extract_json(content)

        # Inject location into evidence spans if provided
        if location:
            for span in result.get("evidence_spans", []):
                if isinstance(span, dict) and not span.get("location"):
                    span["location"] = location
            for ins in result.get("key_insights", []):
                if isinstance(ins, dict) and not ins.get("location"):
                    ins["location"] = location

        # Normalize
        if "key_insights" not in result or not isinstance(result["key_insights"], list):
            result["key_insights"] = []
        if "evidence_spans" not in result or not isinstance(result["evidence_spans"], list):
            result["evidence_spans"] = []
        if "topic_label" not in result:
            result["topic_label"] = ""

        return result

    def activate_memory(self, task: dict, cards: list[dict], output_schema: dict) -> dict:
        """Call DeepSeek to activate recalled cards for the current task."""
        task_desc = task.get("current_task", "")
        intent = task.get("output_intent", "general")
        audience = task.get("audience", "general")
        language = task.get("language", "zh")

        cards_text = []
        for i, item in enumerate(cards[:5], 1):
            card = item.get("card", {})
            fog = card.get("fog_index", {}).get("level", "Foggy")
            core = card.get("core_insight", "")
            seed = card.get("knowledge_seed", "")[:300]
            tags = ", ".join(card.get("topic_tags", []))
            cards_text.append(
                f"Card {i}:\n"
                f"- Tags: {tags}\n"
                f"- Core insight: {core}\n"
                f"- Source snippet: {seed}\n"
                f"- Fog Index: {fog}\n"
            )

        user_prompt = f"""Turn the following saved knowledge cards into usable content for the current task.

Current task: {task_desc}
Output intent: {intent}
Audience: {audience}
Language preference: {language}

Cards:
---
{"\n".join(cards_text)}
---

Return valid JSON:
{{
  "why_these_memories": "Explain why these cards are relevant.",
  "ready_to_use_output": "Copy-ready paragraph matching the intent and audience.",
  "questions_to_ask": ["Question 1", "Question 2"],
  "source_notes": ["Source note 1", "Source note 2"],
  "confidence_note": "Note about confidence based on Fog Index."
}}

Rules:
- Use CARD CONTENT directly. Do not paraphrase into generic language.
- Match the output form to the intent (proposal opening, meeting talking point, CPD reflection, etc.).
- Very Foggy cards must NOT be presented as confirmed facts.
- If multiple cards, synthesize them rather than repeating each one.
- Output ONLY valid JSON, no extra text.
"""

        content = self._call_chat(ACTIVATION_SYSTEM, user_prompt, temperature=0.5)
        result = self._extract_json(content)

        # Normalize
        for key in ["why_these_memories", "ready_to_use_output", "confidence_note"]:
            if key not in result:
                result[key] = ""
        for key in ["questions_to_ask", "source_notes"]:
            if key not in result or not isinstance(result[key], list):
                result[key] = []

        return result


def create_llm_client() -> LLMClient:
    """Factory: create the best available LLM client.

    Environment variables:
      - RECALLBITE_LLM_API_KEY     API key (empty = deterministic fallback)
      - RECALLBITE_LLM_PROVIDER    Provider type: openai (default), ollama
      - RECALLBITE_LLM_BASE_URL    API base URL
      - RECALLBITE_LLM_MODEL       Model name

    Falls back to deterministic local rules when no API key is configured.
    """
    api_key = os.getenv("RECALLBITE_LLM_API_KEY", "").strip()
    if not api_key:
        return DeterministicLLMClient()

    provider = os.getenv("RECALLBITE_LLM_PROVIDER", "openai").lower().strip()
    base_url = os.getenv("RECALLBITE_LLM_BASE_URL", "").strip()
    model = os.getenv("RECALLBITE_LLM_MODEL", "").strip()

    if provider in ("openai", "deepseek", "qwen", "azure"):
        # Default base_url and model if not overridden
        if not base_url:
            base_url = "https://api.deepseek.com"
        if not model:
            model = "deepseek-chat"
        return OpenAILLMClient(api_key=api_key, base_url=base_url, model=model)

    if provider == "ollama":
        if not base_url:
            base_url = "http://localhost:11434/v1"
        if not model:
            model = "llama3"
        return OpenAILLMClient(api_key=api_key, base_url=base_url, model=model)

    # Unknown provider: still try OpenAI-compatible as best-effort
    if not base_url:
        base_url = "https://api.deepseek.com"
    if not model:
        model = "deepseek-chat"
    return OpenAILLMClient(api_key=api_key, base_url=base_url, model=model)


# Backward-compatible alias
DeepSeekLLMClient = OpenAILLMClient
