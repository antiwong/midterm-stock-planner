"""Sentiment model interface and implementations.

This module provides:
- Abstract interface for sentiment models
- Dummy implementation for testing
- Lexicon-based implementation for MVP
- Functions to score text and news items

The design allows easy replacement with more sophisticated models
like FinBERT later.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union
import re
import warnings


class SentimentModel(ABC):
    """Abstract base class for sentiment models.
    
    All sentiment models should inherit from this class and implement
    the score_texts method.
    """
    
    @abstractmethod
    def score_texts(self, texts: List[str]) -> List[float]:
        """
        Score a list of texts for sentiment.
        
        Args:
            texts: List of text strings to score.
        
        Returns:
            List of sentiment scores, one per text.
            Scores should typically be in range [-1, 1] where:
            - -1 = very negative
            - 0 = neutral
            - +1 = very positive
        """
        pass
    
    def score_text(self, text: str) -> float:
        """Score a single text string."""
        return self.score_texts([text])[0]
    
    @property
    def name(self) -> str:
        """Return model name."""
        return self.__class__.__name__


class DummySentimentModel(SentimentModel):
    """
    Dummy sentiment model for testing.
    
    Returns random scores in [-1, 1] range.
    Useful for testing the pipeline without a real model.
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize dummy model.
        
        Args:
            seed: Random seed for reproducibility.
        """
        self.seed = seed
        self._rng = np.random.RandomState(seed)
    
    def score_texts(self, texts: List[str]) -> List[float]:
        """Return random sentiment scores."""
        return self._rng.uniform(-1, 1, len(texts)).tolist()


class LexiconSentimentModel(SentimentModel):
    """
    Simple lexicon-based sentiment model.
    
    Uses a predefined dictionary of positive and negative words
    to compute sentiment scores. This is a simple but interpretable
    baseline that can be replaced with more sophisticated models.
    """
    
    # Default word lists (can be extended or replaced)
    DEFAULT_POSITIVE_WORDS = {
        # Financial positive
        "beat", "beats", "beating", "exceeded", "exceeds", "outperform",
        "outperformed", "upgrade", "upgraded", "upgrades", "buy", "bullish",
        "growth", "gains", "gain", "gained", "rally", "rallied", "surge",
        "surged", "soar", "soared", "rise", "rises", "rising", "rose",
        "increase", "increased", "increases", "profit", "profits",
        "profitable", "strong", "stronger", "strength", "positive",
        "optimistic", "success", "successful", "record", "high", "higher",
        "improve", "improved", "improvement", "boost", "boosted",
        "momentum", "opportunity", "opportunities", "innovation",
        "innovative", "breakthrough", "efficient", "efficiency",
        # General positive
        "good", "great", "excellent", "best", "better", "amazing",
        "impressive", "outstanding", "fantastic", "wonderful",
    }
    
    DEFAULT_NEGATIVE_WORDS = {
        # Financial negative
        "miss", "missed", "misses", "missing", "below", "downgrade",
        "downgraded", "downgrades", "sell", "bearish", "decline",
        "declined", "declines", "declining", "drop", "dropped", "drops",
        "fall", "fell", "falls", "falling", "loss", "losses", "lose",
        "losing", "weak", "weaker", "weakness", "negative", "pessimistic",
        "fail", "failed", "fails", "failure", "low", "lower", "worst",
        "worse", "poor", "disappoint", "disappointed", "disappointing",
        "concern", "concerns", "worried", "worry", "risk", "risks",
        "risky", "danger", "dangerous", "threat", "threatens",
        "uncertain", "uncertainty", "volatile", "volatility",
        # Crisis words
        "crash", "crashed", "crisis", "recession", "bankruptcy",
        "default", "fraud", "scandal", "investigation", "lawsuit",
        "layoff", "layoffs", "cut", "cuts", "cutting",
        # General negative
        "bad", "terrible", "awful", "horrible", "poor", "worst",
    }
    
    DEFAULT_NEGATION_WORDS = {
        "not", "no", "never", "neither", "nobody", "nothing",
        "nowhere", "hardly", "scarcely", "barely", "doesn't",
        "don't", "didn't", "won't", "wouldn't", "couldn't",
        "shouldn't", "isn't", "aren't", "wasn't", "weren't",
    }
    
    def __init__(
        self,
        positive_words: Optional[set] = None,
        negative_words: Optional[set] = None,
        negation_words: Optional[set] = None,
        negation_window: int = 3,
    ):
        """
        Initialize lexicon model.
        
        Args:
            positive_words: Set of positive words. Uses default if None.
            negative_words: Set of negative words. Uses default if None.
            negation_words: Set of negation words. Uses default if None.
            negation_window: Number of words after negation to flip sentiment.
        """
        self.positive_words = positive_words or self.DEFAULT_POSITIVE_WORDS
        self.negative_words = negative_words or self.DEFAULT_NEGATIVE_WORDS
        self.negation_words = negation_words or self.DEFAULT_NEGATION_WORDS
        self.negation_window = negation_window
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Convert to lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        return words
    
    def _score_single_text(self, text: str) -> float:
        """Score a single text string."""
        words = self._tokenize(text)
        
        if len(words) == 0:
            return 0.0
        
        positive_count = 0
        negative_count = 0
        
        # Track negation context
        negation_active = False
        words_since_negation = 0
        
        for word in words:
            # Check for negation
            if word in self.negation_words:
                negation_active = True
                words_since_negation = 0
                continue
            
            # Update negation tracking
            if negation_active:
                words_since_negation += 1
                if words_since_negation > self.negation_window:
                    negation_active = False
            
            # Score the word
            if word in self.positive_words:
                if negation_active:
                    negative_count += 1
                else:
                    positive_count += 1
            elif word in self.negative_words:
                if negation_active:
                    positive_count += 1
                else:
                    negative_count += 1
        
        # Compute normalized score
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        score = (positive_count - negative_count) / total
        return score
    
    def score_texts(self, texts: List[str]) -> List[float]:
        """Score multiple texts."""
        return [self._score_single_text(text) for text in texts]
    
    def get_word_contribution(self, text: str) -> Dict[str, int]:
        """
        Get word-level contributions to sentiment score.
        
        Args:
            text: Text to analyze.
        
        Returns:
            Dictionary mapping words to their contribution (+1 or -1).
        """
        words = self._tokenize(text)
        contributions = {}
        
        negation_active = False
        words_since_negation = 0
        
        for word in words:
            if word in self.negation_words:
                negation_active = True
                words_since_negation = 0
                continue
            
            if negation_active:
                words_since_negation += 1
                if words_since_negation > self.negation_window:
                    negation_active = False
            
            if word in self.positive_words:
                contributions[word] = -1 if negation_active else 1
            elif word in self.negative_words:
                contributions[word] = 1 if negation_active else -1
        
        return contributions


class FinBERTSentimentModel(SentimentModel):
    """
    FinBERT-based sentiment model.
    
    Uses the FinBERT model for financial sentiment analysis.
    This is a placeholder that can be implemented when FinBERT
    is available.
    """
    
    def __init__(self, model_name: str = "ProsusAI/finbert", batch_size: int = 32):
        """
        Initialize FinBERT model.
        
        Args:
            model_name: HuggingFace model name.
            batch_size: Batch size for inference.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None
        self._tokenizer = None
    
    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                self._model.eval()
            except ImportError:
                raise ImportError(
                    "FinBERT requires transformers and torch packages. "
                    "Install with: pip install transformers torch"
                )
    
    def score_texts(self, texts: List[str]) -> List[float]:
        """Score texts using FinBERT."""
        self._load_model()
        
        try:
            import torch
        except ImportError:
            raise ImportError("FinBERT requires torch package.")
        
        scores = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            
            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                
                # FinBERT outputs: [negative, neutral, positive]
                # Convert to [-1, 1] scale
                batch_scores = probs[:, 2] - probs[:, 0]
                scores.extend(batch_scores.tolist())
        
        return scores


def get_sentiment_model(
    model_type: str = "lexicon",
    **kwargs
) -> SentimentModel:
    """
    Factory function to get a sentiment model.
    
    Args:
        model_type: Type of model ("dummy", "lexicon", "finbert").
        **kwargs: Additional arguments for the model.
    
    Returns:
        SentimentModel instance.
    """
    models = {
        "dummy": DummySentimentModel,
        "lexicon": LexiconSentimentModel,
        "finbert": FinBERTSentimentModel,
    }
    
    if model_type not in models:
        raise ValueError(
            f"Unknown model type: {model_type}. "
            f"Available: {list(models.keys())}"
        )
    
    return models[model_type](**kwargs)


def score_texts(
    texts: List[str],
    model: Optional[SentimentModel] = None,
    model_type: str = "lexicon",
) -> List[float]:
    """
    Score a list of texts for sentiment.
    
    Args:
        texts: List of text strings.
        model: Optional pre-initialized model. If None, creates one.
        model_type: Type of model to create if model is None.
    
    Returns:
        List of sentiment scores in [-1, 1] range.
    """
    if model is None:
        model = get_sentiment_model(model_type)
    
    return model.score_texts(texts)


def score_news_items(
    news_df: pd.DataFrame,
    text_col: str = "headline",
    model: Optional[SentimentModel] = None,
    model_type: str = "lexicon",
    output_col: str = "sentiment_raw",
) -> pd.DataFrame:
    """
    Score news items and add sentiment column.
    
    Args:
        news_df: News DataFrame with text column.
        text_col: Column containing text to score.
        model: Optional pre-initialized sentiment model.
        model_type: Type of model to create if model is None.
        output_col: Name for output sentiment column.
    
    Returns:
        DataFrame with added sentiment column.
    """
    df = news_df.copy()
    
    if text_col not in df.columns:
        raise ValueError(f"Text column '{text_col}' not found in DataFrame")
    
    # Handle missing/empty text
    texts = df[text_col].fillna("").astype(str).tolist()
    
    # Score texts
    scores = score_texts(texts, model=model, model_type=model_type)
    
    df[output_col] = scores
    
    return df


class TextBlobSentimentModel(SentimentModel):
    """
    TextBlob-based sentiment model.
    
    Uses TextBlob's built-in sentiment analysis which combines
    pattern-based and lexical approaches.
    """
    
    def __init__(self):
        """Initialize TextBlob model."""
        self._check_available()
    
    def _check_available(self) -> bool:
        """Check if TextBlob is available."""
        try:
            from textblob import TextBlob
            self._textblob = TextBlob
            return True
        except ImportError:
            raise ImportError(
                "TextBlob requires textblob package. "
                "Install with: pip install textblob"
            )
    
    def score_texts(self, texts: List[str]) -> List[float]:
        """Score texts using TextBlob sentiment."""
        scores = []
        for text in texts:
            blob = self._textblob(text)
            # TextBlob polarity is already in [-1, 1]
            scores.append(blob.sentiment.polarity)
        return scores
    
    def get_detailed_sentiment(self, text: str) -> Dict[str, float]:
        """
        Get detailed sentiment including polarity and subjectivity.
        
        Args:
            text: Text to analyze.
            
        Returns:
            Dictionary with polarity, subjectivity, and sentiment label.
        """
        blob = self._textblob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "sentiment": label,
        }


# Update the factory function to include TextBlob
_MODEL_REGISTRY = {
    "dummy": DummySentimentModel,
    "lexicon": LexiconSentimentModel,
    "finbert": FinBERTSentimentModel,
    "textblob": TextBlobSentimentModel,
}


def get_sentiment_model(
    model_type: str = "lexicon",
    **kwargs
) -> SentimentModel:
    """
    Factory function to get a sentiment model.
    
    Args:
        model_type: Type of model ("dummy", "lexicon", "textblob", "finbert").
        **kwargs: Additional arguments for the model.
    
    Returns:
        SentimentModel instance.
    """
    if model_type not in _MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model type: {model_type}. "
            f"Available: {list(_MODEL_REGISTRY.keys())}"
        )
    
    return _MODEL_REGISTRY[model_type](**kwargs)
