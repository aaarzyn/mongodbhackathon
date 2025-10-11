"""Advanced LLM-based judge using Fireworks for handoff evaluation.

Produces comprehensive JSON-structured judgments including:
- Fidelity (information preservation)
- Drift (semantic deviation)
- Completeness (coverage of original context)
- Consistency (logical coherence)
- Key facts preserved and lost
- Detailed reasoning and recommendations

Uses chain-of-thought reasoning for better accuracy.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from backend.config import get_settings
from backend.providers.fireworks import FireworksJudge, FireworksProviderError

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


@dataclass
class HandoffEvaluation:
    """Structured evaluation result."""
    fidelity: float  # 0.0-1.0: How well information was preserved
    drift: float  # 0.0-1.0: Semantic deviation from original
    completeness: float  # 0.0-1.0: Coverage of original information
    consistency: float  # 0.0-1.0: Internal logical coherence
    preserved_facts: List[str]  # Key information successfully transferred
    lost_facts: List[str]  # Important information that was dropped
    added_facts: List[str]  # New information introduced (potential hallucination)
    reasoning: str  # Explanation of the evaluation
    quality_grade: str  # A, B, C, D, F
    recommendations: List[str]  # Suggestions for improvement
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'fidelity': self.fidelity,
            'drift': self.drift,
            'completeness': self.completeness,
            'consistency': self.consistency,
            'preserved': self.preserved_facts,
            'lost': self.lost_facts,
            'added': self.added_facts,
            'reasoning': self.reasoning,
            'grade': self.quality_grade,
            'recommendations': self.recommendations,
            'overall_score': self._calculate_overall_score(),
        }
    
    def _calculate_overall_score(self) -> float:
        """Calculate weighted overall quality score."""
        return (
            self.fidelity * 0.35 +
            (1 - self.drift) * 0.25 +
            self.completeness * 0.25 +
            self.consistency * 0.15
        )


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text, handling various formats and nested structures."""
    if not text:
        return None
    
    # Clean up common markdown artifacts
    text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try to extract from code blocks (markdown format)
    code_block_patterns = [
        r'```json\s*(\{[\s\S]*?\})\s*```',
        r'```\s*(\{[\s\S]*?\})\s*```',
        r'<json>\s*(\{[\s\S]*?\})\s*</json>',
    ]
    
    for pattern in code_block_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                continue
    
    # Try to find any JSON object in the text
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    
    # Last resort: try to find content between first { and last }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except Exception:
            pass
    
    logger.warning(f"Failed to extract JSON from text: {text[:200]}...")
    return None


def _calculate_grade(overall_score: float) -> str:
    """Convert overall score to letter grade."""
    if overall_score >= 0.90:
        return "A"
    elif overall_score >= 0.80:
        return "B"
    elif overall_score >= 0.70:
        return "C"
    elif overall_score >= 0.60:
        return "D"
    else:
        return "F"


def judge_handoff_via_fireworks(
    *,
    context_sent: str,
    context_received: str,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    use_chain_of_thought: bool = True,
) -> Optional[Dict[str, Any]]:
    """Advanced handoff evaluation using Fireworks LLM judge.
    
    Performs comprehensive analysis of information transfer quality between agents.
    
    Args:
        context_sent: The context/information sent by the source agent
        context_received: The context/information received by the target agent
        temperature: LLM temperature (0.0 = deterministic, higher = more creative)
        max_tokens: Maximum tokens for response
        use_chain_of_thought: Whether to use reasoning steps for better accuracy
        
    Returns:
        Dictionary with comprehensive evaluation metrics, or None on failure
    """
    settings = get_settings()
    judge = FireworksJudge(settings)
    
    if not judge.available():
        logger.warning("Fireworks judge not available (no API key)")
        return None

    # Enhanced system prompt for better instruction following
    system = (
        "You are an expert AI system evaluator specializing in information transfer analysis. "
        "You assess how well information is preserved when passed between AI agents. "
        "You MUST respond with ONLY valid JSON - no explanations outside the JSON structure. "
        "Be precise, analytical, and thorough in your evaluation."
    )
    
    # Smart truncation - preserve structure
    def smart_truncate(text: str, max_chars: int = 3000) -> str:
        """Truncate while trying to preserve structure."""
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at a natural boundary
        truncated = text[:max_chars]
        
        # Find last complete sentence or list item
        boundaries = ['. ', '\n', '- ', '}', ']']
        for boundary in boundaries:
            last_boundary = truncated.rfind(boundary)
            if last_boundary > max_chars * 0.8:  # At least 80% of desired length
                return truncated[:last_boundary + len(boundary)] + "...[truncated]"
        
        return truncated + "...[truncated]"
    
    sent_truncated = smart_truncate(context_sent)
    recv_truncated = smart_truncate(context_received)
    
    # Enhanced prompt with chain-of-thought reasoning
    if use_chain_of_thought:
        user = f"""Analyze this agent-to-agent information handoff:

**CONTEXT SENT (Source Agent):**
{sent_truncated}

**CONTEXT RECEIVED (Target Agent):**
{recv_truncated}

Evaluate the quality of information transfer. Think step-by-step:

1. **Fidelity Analysis**: What percentage of the original information was accurately preserved?
2. **Drift Detection**: How much did the meaning/semantics deviate from the original?
3. **Completeness Check**: What proportion of the source context is covered?
4. **Consistency Validation**: Is the received context internally coherent?
5. **Fact Tracking**: Which specific facts were preserved, lost, or added?

Respond with ONLY this JSON structure (no other text):

{{
  "fidelity": <float 0.0-1.0>,
  "drift": <float 0.0-1.0>,
  "completeness": <float 0.0-1.0>,
  "consistency": <float 0.0-1.0>,
  "preserved": ["fact1", "fact2", ...],
  "lost": ["missing_fact1", "missing_fact2", ...],
  "added": ["new_fact1", "new_fact2", ...],
  "reasoning": "Brief explanation of scores",
  "recommendations": ["improvement1", "improvement2", ...]
}}

Guidelines:
- fidelity: 1.0 = perfect preservation, 0.0 = completely different
- drift: 0.0 = no semantic change, 1.0 = completely different meaning
- completeness: 1.0 = all info covered, 0.0 = nothing covered
- consistency: 1.0 = perfectly coherent, 0.0 = contradictory
- preserved: List 5-10 key facts that survived the handoff
- lost: List important facts that were dropped (if any)
- added: List facts in received but not in sent (potential hallucinations)
- reasoning: 2-3 sentences explaining the evaluation
- recommendations: 2-3 actionable suggestions for improvement

JSON Response:"""
    else:
        # Simpler prompt without chain-of-thought
        user = f"""Evaluate this information handoff:

SENT:
{sent_truncated}

RECEIVED:
{recv_truncated}

Respond with ONLY valid JSON (no other text):

{{
  "fidelity": <0.0-1.0>,
  "drift": <0.0-1.0>,
  "completeness": <0.0-1.0>,
  "consistency": <0.0-1.0>,
  "preserved": ["fact1", "fact2"],
  "lost": ["missing1"],
  "added": ["new1"],
  "reasoning": "explanation",
  "recommendations": ["suggestion1"]
}}

JSON:"""
    
    try:
        logger.debug("Sending evaluation request to Fireworks...")
        out = judge.judge_text(
            system_prompt=system,
            user_prompt=user,
            temperature=temperature,
            max_tokens=max_tokens
        )
        logger.debug(f"Fireworks response length: {len(out) if out else 0} chars")
        logger.debug(f"Fireworks response preview: {out[:500] if out else 'None'}...")
        
    except FireworksProviderError as e:
        logger.error(f"Fireworks provider error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error from Fireworks: {e}", exc_info=True)
        return None

    if not out:
        logger.warning("Fireworks returned empty/None response")
        return None
    
    # Extract and parse JSON
    data = _extract_json(out)
    
    if not isinstance(data, dict):
        logger.warning(f"Failed to extract valid JSON dict from response. Raw output: {out[:200]}")
        return _create_fallback_evaluation(context_sent, context_received)
    
    logger.debug(f"Parsed JSON data: {json.dumps(data, indent=2)}")
    
    # Validate and normalize the response
    try:
        evaluation = _normalize_evaluation(data)
        result = evaluation.to_dict()
        
        logger.info(
            f"Handoff evaluation complete: "
            f"Fidelity={evaluation.fidelity:.2f}, "
            f"Drift={evaluation.drift:.2f}, "
            f"Grade={evaluation.quality_grade}, "
            f"Overall={result['overall_score']:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to normalize evaluation: {e}", exc_info=True)
        return _create_fallback_evaluation(context_sent, context_received)


def _normalize_evaluation(data: Dict[str, Any]) -> HandoffEvaluation:
    """Normalize and validate evaluation data into structured format.
    
    Args:
        data: Raw dictionary from LLM
        
    Returns:
        Validated HandoffEvaluation object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract and validate numeric scores
    def validate_score(key: str, default: float = 0.5) -> float:
        value = data.get(key, default)
        try:
            score = float(value)
            return max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            logger.warning(f"Invalid {key} value: {value}, using default {default}")
            return default
    
    fidelity = validate_score('fidelity', 0.5)
    drift = validate_score('drift', 0.5)
    completeness = validate_score('completeness', 0.5)
    consistency = validate_score('consistency', 0.8)  # Default to optimistic
    
    # Extract and validate lists
    def validate_list(key: str, max_items: int = 20) -> List[str]:
        value = data.get(key, [])
        if not isinstance(value, list):
            logger.warning(f"Invalid {key} value (not a list): {value}")
            return []
        return [str(x)[:300] for x in value[:max_items]]
    
    preserved_facts = validate_list('preserved', 15)
    lost_facts = validate_list('lost', 10)
    added_facts = validate_list('added', 10)
    recommendations = validate_list('recommendations', 5)
    
    # Extract reasoning
    reasoning = str(data.get('reasoning', 'No detailed reasoning provided.'))[:1000]
    
    # Calculate overall score and grade
    evaluation = HandoffEvaluation(
        fidelity=fidelity,
        drift=drift,
        completeness=completeness,
        consistency=consistency,
        preserved_facts=preserved_facts,
        lost_facts=lost_facts,
        added_facts=added_facts,
        reasoning=reasoning,
        quality_grade='',  # Will be set below
        recommendations=recommendations,
    )
    
    # Set grade based on overall score
    evaluation.quality_grade = _calculate_grade(evaluation._calculate_overall_score())
    
    return evaluation


def _create_fallback_evaluation(
    context_sent: str,
    context_received: str
) -> Dict[str, Any]:
    """Create a basic heuristic-based evaluation when LLM fails.
    
    Args:
        context_sent: Source context
        context_received: Received context
        
    Returns:
        Basic evaluation dictionary
    """
    logger.warning("Creating fallback evaluation based on heuristics")
    
    # Simple heuristic: compare lengths and keyword overlap
    sent_len = len(context_sent)
    recv_len = len(context_received)
    
    # Length-based completeness estimate
    length_ratio = min(recv_len / max(sent_len, 1), 1.0)
    
    # Simple keyword overlap (very rough fidelity estimate)
    sent_words = set(context_sent.lower().split())
    recv_words = set(context_received.lower().split())
    
    overlap = len(sent_words & recv_words)
    union = len(sent_words | recv_words)
    keyword_overlap = overlap / max(union, 1)
    
    # Estimate metrics
    fidelity = (length_ratio + keyword_overlap) / 2
    drift = 1.0 - keyword_overlap
    completeness = length_ratio
    consistency = 0.7  # Assume reasonable consistency
    
    evaluation = HandoffEvaluation(
        fidelity=fidelity,
        drift=drift,
        completeness=completeness,
        consistency=consistency,
        preserved_facts=["[Heuristic evaluation - detailed analysis unavailable]"],
        lost_facts=[],
        added_facts=[],
        reasoning=(
            "Fallback heuristic evaluation due to LLM parsing failure. "
            f"Length ratio: {length_ratio:.2f}, Keyword overlap: {keyword_overlap:.2f}" ),
        quality_grade=_calculate_grade((fidelity + (1 - drift) + completeness) / 3),
        recommendations=[
            "Re-run evaluation with proper LLM response",
            "Check context format compatibility",
        ],
    )
    
    return evaluation.to_dict()


def batch_judge_handoffs(
    handoffs: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> List[Optional[Dict[str, Any]]]:
    """Evaluate multiple handoffs in batch.
    
    Args:
        handoffs: List of dicts with 'context_sent' and 'context_received' keys
        temperature: LLM temperature
        max_tokens: Max tokens per evaluation
        
    Returns:
        List of evaluation results (None for failures)
    """
    results = []
    
    for i, handoff in enumerate(handoffs):
        logger.info(f"Evaluating handoff {i + 1}/{len(handoffs)}...")
        
        try:
            result = judge_handoff_via_fireworks(
                context_sent=handoff['context_sent'],
                context_received=handoff['context_received'],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            results.append(result)
            
        except Exception as e:
            logger.error(f"Failed to evaluate handoff {i + 1}: {e}")
            results.append(None)
    
    return results