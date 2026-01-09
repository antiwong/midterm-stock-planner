"""LLM-powered sentiment analysis."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check for LLM libraries
OPENAI_AVAILABLE = False
GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    pass

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    pass


@dataclass
class LLMAnalysisResult:
    """Result from LLM sentiment analysis."""
    sentiment_score: float  # -1 to 1
    sentiment_label: str  # positive, negative, neutral
    summary: str
    key_themes: List[str]
    risks: List[str]
    opportunities: List[str]
    impact_score: int  # 1-5
    confidence: float  # 0-1
    raw_response: Optional[Dict] = None


class LLMSentimentAnalyzer:
    """LLM-powered sentiment analysis using OpenAI or Gemini."""
    
    def __init__(
        self,
        provider: str = "auto",
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM analyzer.
        
        Args:
            provider: LLM provider ("openai", "gemini", or "auto")
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            gemini_api_key: Gemini API key (or set GEMINI_API_KEY env var)
            model: Model to use (defaults to gpt-3.5-turbo or gemini-pro)
        """
        self.provider = provider
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
        self._client = None
        self._setup_client()
    
    def _setup_client(self) -> None:
        """Setup the LLM client based on available providers."""
        if self.provider == "auto":
            # Try OpenAI first, then Gemini
            if OPENAI_AVAILABLE and self.openai_api_key:
                self.provider = "openai"
            elif GEMINI_AVAILABLE and self.gemini_api_key:
                self.provider = "gemini"
            else:
                logger.warning("No LLM provider available. Install openai or google-generativeai")
                return
        
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                logger.error("OpenAI package not installed. pip install openai")
                return
            if not self.openai_api_key:
                logger.warning("OpenAI API key not configured")
                return
            self._client = openai.OpenAI(api_key=self.openai_api_key)
            self.model = self.model or "gpt-3.5-turbo"
            logger.info(f"Initialized OpenAI client with model {self.model}")
            
        elif self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                logger.error("Gemini package not installed. pip install google-generativeai")
                return
            if not self.gemini_api_key:
                logger.warning("Gemini API key not configured")
                return
            genai.configure(api_key=self.gemini_api_key)
            
            # Try different model names in order of preference
            model_names = [self.model] if self.model else []
            model_names.extend([
                'gemini-2.0-flash-exp',
                'gemini-1.5-flash-latest',
                'gemini-1.5-pro-latest',
                'gemini-pro',
            ])
            
            for name in model_names:
                if name is None:
                    continue
                try:
                    self._client = genai.GenerativeModel(name)
                    self.model = name
                    logger.info(f"Initialized Gemini client with model {self.model}")
                    break
                except Exception:
                    continue
    
    def is_available(self) -> bool:
        """Check if LLM analysis is available."""
        return self._client is not None
    
    def analyze_article(
        self,
        headline: str,
        body: str,
        ticker: str,
        company_name: Optional[str] = None,
    ) -> LLMAnalysisResult:
        """
        Analyze a single article using LLM.
        
        Args:
            headline: Article headline
            body: Article body text
            ticker: Stock ticker symbol
            company_name: Company name (optional)
            
        Returns:
            LLMAnalysisResult with detailed analysis
        """
        if not self.is_available():
            # Return neutral result if LLM not available
            return LLMAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                summary="LLM analysis not available",
                key_themes=[],
                risks=[],
                opportunities=[],
                impact_score=3,
                confidence=0.0,
            )
        
        company = company_name or ticker
        prompt = self._build_analysis_prompt(headline, body, ticker, company)
        
        try:
            if self.provider == "openai":
                return self._analyze_with_openai(prompt)
            elif self.provider == "gemini":
                return self._analyze_with_gemini(prompt)
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return LLMAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                summary=f"Analysis failed: {str(e)[:100]}",
                key_themes=[],
                risks=[],
                opportunities=[],
                impact_score=3,
                confidence=0.0,
            )
    
    def _build_analysis_prompt(
        self,
        headline: str,
        body: str,
        ticker: str,
        company: str,
    ) -> str:
        """Build the analysis prompt."""
        return f"""Analyze the following financial news article about {company} ({ticker}).

Headline: {headline}

Body: {body[:2000]}

Provide a JSON response with exactly this structure:
{{
    "sentiment_score": <float from -1.0 to 1.0>,
    "sentiment_label": "<positive|negative|neutral>",
    "summary": "<2-3 sentence summary>",
    "key_themes": ["<theme1>", "<theme2>"],
    "risks": ["<risk1>", "<risk2>"],
    "opportunities": ["<opportunity1>", "<opportunity2>"],
    "impact_score": <integer from 1 to 5, where 5 is highest impact>
}}

Return ONLY valid JSON, no other text."""
    
    def _analyze_with_openai(self, prompt: str) -> LLMAnalysisResult:
        """Analyze using OpenAI."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a financial analyst. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500,
        )
        
        text = response.choices[0].message.content
        return self._parse_response(text)
    
    def _analyze_with_gemini(self, prompt: str) -> LLMAnalysisResult:
        """Analyze using Gemini."""
        response = self._client.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 500,
            }
        )
        
        text = response.text
        return self._parse_response(text)
    
    def _parse_response(self, text: str) -> LLMAnalysisResult:
        """Parse LLM response into result object."""
        # Clean up response
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            data = json.loads(text)
            return LLMAnalysisResult(
                sentiment_score=float(data.get("sentiment_score", 0)),
                sentiment_label=data.get("sentiment_label", "neutral"),
                summary=data.get("summary", ""),
                key_themes=data.get("key_themes", []),
                risks=data.get("risks", []),
                opportunities=data.get("opportunities", []),
                impact_score=int(data.get("impact_score", 3)),
                confidence=0.8,
                raw_response=data,
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return LLMAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                summary=text[:200],
                key_themes=[],
                risks=[],
                opportunities=[],
                impact_score=3,
                confidence=0.3,
            )
    
    def analyze_batch(
        self,
        articles: List[Dict[str, str]],
        ticker: str,
    ) -> List[LLMAnalysisResult]:
        """
        Analyze multiple articles.
        
        Args:
            articles: List of {"headline": str, "body": str} dicts
            ticker: Stock ticker symbol
            
        Returns:
            List of LLMAnalysisResult objects
        """
        results = []
        for article in articles:
            result = self.analyze_article(
                headline=article.get("headline", ""),
                body=article.get("body", ""),
                ticker=ticker,
            )
            results.append(result)
        return results
