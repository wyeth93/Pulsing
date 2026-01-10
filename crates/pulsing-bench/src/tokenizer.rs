//! Tokenizer service for accurate token counting
//!
//! This module provides tokenizer functionality using HuggingFace tokenizers
//! for accurate input/output token counting.

use std::sync::Arc;
use tokenizers::{FromPretrainedParameters, Tokenizer};
use tracing::{info, warn};

/// Tokenizer service for token counting
#[derive(Clone)]
pub struct TokenizerService {
    tokenizer: Arc<Tokenizer>,
    model_name: String,
}

impl TokenizerService {
    /// Create a new tokenizer service from a HuggingFace model name
    ///
    /// # Arguments
    /// * `model_name` - HuggingFace model name (e.g., "Qwen/Qwen3-0.6B")
    /// * `hf_token` - Optional HuggingFace token for private models
    pub fn from_pretrained(model_name: &str, hf_token: Option<String>) -> anyhow::Result<Self> {
        info!("Loading tokenizer for model: {}", model_name);

        let params = FromPretrainedParameters {
            token: hf_token,
            ..Default::default()
        };

        let tokenizer = Tokenizer::from_pretrained(model_name, Some(params))
            .map_err(|e| anyhow::anyhow!("Failed to load tokenizer for {}: {}", model_name, e))?;

        info!("Tokenizer loaded successfully for {}", model_name);

        Ok(Self {
            tokenizer: Arc::new(tokenizer),
            model_name: model_name.to_string(),
        })
    }

    /// Count tokens in a text string
    pub fn count_tokens(&self, text: &str) -> u64 {
        match self.tokenizer.encode(text, false) {
            Ok(encoding) => encoding.get_ids().len() as u64,
            Err(e) => {
                warn!("Failed to encode text: {}, using estimate", e);
                // Fallback to rough estimate
                (text.len() / 4) as u64
            }
        }
    }

    /// Encode text to token IDs
    pub fn encode(&self, text: &str) -> anyhow::Result<Vec<u32>> {
        let encoding = self
            .tokenizer
            .encode(text, false)
            .map_err(|e| anyhow::anyhow!("Failed to encode: {}", e))?;
        Ok(encoding.get_ids().to_vec())
    }

    /// Decode token IDs to text
    pub fn decode(&self, ids: &[u32]) -> anyhow::Result<String> {
        self.tokenizer
            .decode(ids, true)
            .map_err(|e| anyhow::anyhow!("Failed to decode: {}", e))
    }

    /// Get the model name
    pub fn model_name(&self) -> &str {
        &self.model_name
    }

    /// Get vocabulary size
    pub fn vocab_size(&self) -> usize {
        self.tokenizer.get_vocab_size(true)
    }
}

/// Fallback tokenizer that uses character-based estimation
/// when no real tokenizer is available
#[derive(Clone, Default)]
pub struct EstimateTokenizer;

impl EstimateTokenizer {
    /// Estimate token count based on word count
    /// Assumes roughly 1.3 tokens per word (common for English text)
    pub fn count_tokens(&self, text: &str) -> u64 {
        let spaces = text.chars().filter(|c| c.is_whitespace()).count();
        let words = spaces + 1;

        // Rough heuristic: ~1.3 tokens per word for English
        let estimate = (words as f64 * 1.3).ceil() as u64;

        // Ensure at least 1 token
        estimate.max(1)
    }
}

/// Token counter enum that can be either a real tokenizer or an estimator
#[derive(Clone)]
pub enum TokenCounter {
    /// Real HuggingFace tokenizer
    Real(TokenizerService),
    /// Estimation-based counter (fallback)
    Estimate(EstimateTokenizer),
}

impl TokenCounter {
    /// Create a real tokenizer
    pub fn real(model_name: &str, hf_token: Option<String>) -> anyhow::Result<Self> {
        Ok(Self::Real(TokenizerService::from_pretrained(
            model_name, hf_token,
        )?))
    }

    /// Create an estimate-based tokenizer
    pub fn estimate() -> Self {
        Self::Estimate(EstimateTokenizer)
    }

    /// Count tokens in text
    pub fn count_tokens(&self, text: &str) -> u64 {
        match self {
            Self::Real(t) => t.count_tokens(text),
            Self::Estimate(e) => e.count_tokens(text),
        }
    }

    /// Check if this is a real tokenizer
    pub fn is_real(&self) -> bool {
        matches!(self, Self::Real(_))
    }
}

impl Default for TokenCounter {
    fn default() -> Self {
        Self::Estimate(EstimateTokenizer)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_estimate_tokenizer() {
        let estimator = EstimateTokenizer;

        // Simple English text (5 words -> ~7 tokens)
        let text = "Hello, how are you today?";
        let tokens = estimator.count_tokens(text);
        assert!(tokens >= 5);

        // Empty text (0 spaces -> 1 word -> ~2 tokens)
        let empty = "";
        let tokens = estimator.count_tokens(empty);
        assert!(tokens >= 1);

        // Long text (12 words -> ~16 tokens)
        let long_text = "This is a longer piece of text that should have more tokens.";
        let tokens = estimator.count_tokens(long_text);
        assert!(tokens > 10);
    }

    #[test]
    fn test_token_counter_default() {
        let counter = TokenCounter::default();
        assert!(!counter.is_real());

        let tokens = counter.count_tokens("Hello world");
        assert!(tokens > 0);
    }

    #[test]
    fn test_estimate_tokenizer_default() {
        let estimator = EstimateTokenizer;
        let tokens = estimator.count_tokens("test");
        assert!(tokens >= 1);
    }

    #[test]
    fn test_estimate_tokenizer_single_word() {
        let estimator = EstimateTokenizer;
        // Single word with no spaces = 1 word * 1.3 = 2 tokens (ceil)
        let tokens = estimator.count_tokens("Hello");
        assert_eq!(tokens, 2);
    }

    #[test]
    fn test_estimate_tokenizer_multiple_spaces() {
        let estimator = EstimateTokenizer;
        // "a  b  c" has 4 spaces, so 5 words * 1.3 = 6.5 -> 7 tokens
        let tokens = estimator.count_tokens("a  b  c");
        assert!(tokens >= 5);
    }

    #[test]
    fn test_estimate_tokenizer_whitespace_types() {
        let estimator = EstimateTokenizer;
        // Text with tabs and newlines
        let text = "Hello\tworld\ntest";
        let tokens = estimator.count_tokens(text);
        // 2 whitespace chars = 3 words * 1.3 = 4 tokens
        assert!(tokens >= 3);
    }

    #[test]
    fn test_estimate_tokenizer_unicode() {
        let estimator = EstimateTokenizer;
        // Chinese text
        let tokens = estimator.count_tokens("你好 世界");
        assert!(tokens >= 2);

        // Emojis
        let tokens = estimator.count_tokens("Hello 👋 World 🌍");
        // 3 spaces = 4 words * 1.3 = 6 tokens
        assert!(tokens >= 4);
    }

    #[test]
    fn test_estimate_tokenizer_min_one() {
        let estimator = EstimateTokenizer;
        // Even empty string should return at least 1 token
        let tokens = estimator.count_tokens("");
        assert!(tokens >= 1);
    }

    #[test]
    fn test_token_counter_estimate() {
        let counter = TokenCounter::estimate();
        assert!(!counter.is_real());

        let tokens = counter.count_tokens("Hello world");
        assert!(tokens > 0);
    }

    #[test]
    fn test_token_counter_is_real() {
        let estimate_counter = TokenCounter::estimate();
        assert!(!estimate_counter.is_real());

        let default_counter = TokenCounter::default();
        assert!(!default_counter.is_real());
    }

    #[test]
    fn test_token_counter_estimate_consistency() {
        let counter = TokenCounter::estimate();

        let text = "This is a test sentence for token counting.";
        let tokens1 = counter.count_tokens(text);
        let tokens2 = counter.count_tokens(text);

        // Same text should always produce same count
        assert_eq!(tokens1, tokens2);
    }

    #[test]
    fn test_token_counter_estimate_different_texts() {
        let counter = TokenCounter::estimate();

        let short = "Hello";
        let long = "Hello world this is a much longer sentence with more words";

        let short_tokens = counter.count_tokens(short);
        let long_tokens = counter.count_tokens(long);

        // Longer text should have more tokens
        assert!(long_tokens > short_tokens);
    }

    #[test]
    fn test_token_counter_clone() {
        let counter1 = TokenCounter::estimate();
        let counter2 = counter1.clone();

        // Both should produce same results
        let text = "Test text";
        assert_eq!(counter1.count_tokens(text), counter2.count_tokens(text));
    }

    #[test]
    fn test_estimate_tokenizer_clone() {
        let est1 = EstimateTokenizer;
        let est2 = est1.clone();

        let text = "Test";
        assert_eq!(est1.count_tokens(text), est2.count_tokens(text));
    }

    #[test]
    fn test_estimate_tokenizer_very_long_text() {
        let estimator = EstimateTokenizer;

        // Generate a very long text
        let long_text = "word ".repeat(1000);
        let tokens = estimator.count_tokens(&long_text);

        // Should be approximately 1000 * 1.3 = 1300 tokens
        assert!(tokens >= 1000);
        assert!(tokens <= 1500);
    }

    #[test]
    fn test_estimate_tokenizer_special_characters() {
        let estimator = EstimateTokenizer;

        // Text with special characters but no spaces
        let text = "hello@world.com";
        let tokens = estimator.count_tokens(text);
        // 0 spaces = 1 word * 1.3 = 2 tokens
        assert_eq!(tokens, 2);
    }

    #[test]
    fn test_estimate_tokenizer_only_spaces() {
        let estimator = EstimateTokenizer;

        // Only spaces
        let text = "     ";
        let tokens = estimator.count_tokens(text);
        // 5 spaces = 6 words * 1.3 = 8 tokens
        assert!(tokens >= 6);
    }

    // Note: Real tokenizer tests require network access and are marked as ignored
    // They can be run manually with: cargo test -- --ignored

    #[test]
    #[ignore]
    fn test_real_tokenizer_gpt2() {
        // This test requires network access to download tokenizer
        let result = TokenizerService::from_pretrained("gpt2", None);
        if let Ok(tokenizer) = result {
            assert_eq!(tokenizer.model_name(), "gpt2");

            // Test token counting
            let text = "Hello, world!";
            let tokens = tokenizer.count_tokens(text);
            assert!(tokens > 0);

            // Test encode/decode
            let encoded = tokenizer.encode(text).unwrap();
            assert!(!encoded.is_empty());

            let decoded = tokenizer.decode(&encoded).unwrap();
            assert!(!decoded.is_empty());
        }
    }

    #[test]
    #[ignore]
    fn test_token_counter_real() {
        // This test requires network access
        let result = TokenCounter::real("gpt2", None);
        if let Ok(counter) = result {
            assert!(counter.is_real());

            let tokens = counter.count_tokens("Hello world");
            assert!(tokens > 0);
        }
    }
}
