"""
LLM evaluator for quality scoring.

Calls Claude API to evaluate search quality.
"""

import json
import os
from typing import Dict, Optional, Tuple
import asyncio

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMEvaluator:
    """
    LLM-based quality evaluator.

    Uses Claude API to evaluate search quality with:
    - Async execution
    - Timeout handling
    - Error recovery
    - Token counting
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-haiku-20240307",
        timeout: float = 30.0
    ):
        """
        Initialize evaluator.

        Args:
            api_key: Anthropic API key (or from env)
            model: Model to use
            timeout: Request timeout in seconds
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        # Get API key
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter"
            )

        self.model = model
        self.timeout = timeout
        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def evaluate_async(
        self,
        prompt: str,
        max_tokens: int = 1024
    ) -> Tuple[Dict, Dict]:
        """
        Evaluate quality asynchronously.

        Args:
            prompt: Evaluation prompt
            max_tokens: Maximum response tokens

        Returns:
            Tuple of (evaluation_dict, usage_dict)
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._call_api,
                    prompt,
                    max_tokens
                ),
                timeout=self.timeout
            )

            return response

        except asyncio.TimeoutError:
            raise TimeoutError(f"API call timed out after {self.timeout}s")
        except Exception as e:
            raise Exception(f"API call failed: {e}")

    def evaluate(
        self,
        prompt: str,
        max_tokens: int = 1024
    ) -> Tuple[Dict, Dict]:
        """
        Evaluate quality synchronously.

        Args:
            prompt: Evaluation prompt
            max_tokens: Maximum response tokens

        Returns:
            Tuple of (evaluation_dict, usage_dict)
        """
        return self._call_api(prompt, max_tokens)

    def _call_api(
        self,
        prompt: str,
        max_tokens: int
    ) -> Tuple[Dict, Dict]:
        """
        Make API call to Claude.

        Args:
            prompt: Evaluation prompt
            max_tokens: Maximum response tokens

        Returns:
            Tuple of (evaluation_dict, usage_dict)
        """
        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            response_text = message.content[0].text

            # Parse JSON from response
            evaluation = self._parse_json_response(response_text)

            # Get usage stats
            usage = {
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens,
                'total_tokens': message.usage.input_tokens + message.usage.output_tokens
            }

            return evaluation, usage

        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {e}")
        except Exception as e:
            raise Exception(f"Evaluation failed: {e}")

    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse JSON from LLM response.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in response
        # LLM might include explanation before/after JSON

        # Look for JSON block
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')

        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in response")

        json_text = response_text[json_start:json_end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in response: {e}")

    def validate_response(self, evaluation: Dict) -> bool:
        """
        Validate evaluation response has required fields.

        Args:
            evaluation: Parsed evaluation dictionary

        Returns:
            True if valid
        """
        required_fields = [
            'overall_quality',
            'relevance',
            'accuracy',
            'helpfulness',
            'coverage',
            'quality_rating'
        ]

        for field in required_fields:
            if field not in evaluation:
                return False

        # Validate ranges
        for field in ['overall_quality', 'relevance', 'accuracy', 'helpfulness', 'coverage']:
            value = evaluation.get(field)
            if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                return False

        # Validate rating
        valid_ratings = ['excellent', 'good', 'acceptable', 'poor']
        if evaluation.get('quality_rating') not in valid_ratings:
            return False

        return True

    @staticmethod
    def is_available() -> bool:
        """Check if LLM evaluation is available."""
        return ANTHROPIC_AVAILABLE and 'ANTHROPIC_API_KEY' in os.environ
