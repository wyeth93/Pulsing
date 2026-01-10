//! Message definitions for the benchmark actor system

use serde::{Deserialize, Serialize};

// ============================================================================
// Configuration Messages
// ============================================================================

/// Benchmark configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkConfig {
    /// Target URL
    pub url: String,
    /// API key for authentication
    pub api_key: String,
    /// Model name
    pub model_name: String,
    /// Tokenizer name (HuggingFace model name)
    pub tokenizer_name: Option<String>,
    /// Maximum virtual users (concurrent requests)
    pub max_vus: u64,
    /// Test duration in seconds
    pub duration_secs: u64,
    /// Target request rate (requests per second), None for max throughput
    pub rate: Option<f64>,
    /// Warmup duration in seconds
    pub warmup_secs: u64,
    /// Benchmark kind: "throughput", "sweep", "rate", "csweep"
    pub benchmark_kind: String,
    /// Number of rate steps for sweep
    pub num_rates: u64,
    /// Specific rates for rate benchmark
    pub rates: Option<Vec<f64>>,
}

impl Default for BenchmarkConfig {
    fn default() -> Self {
        Self {
            url: "http://localhost:8000".to_string(),
            api_key: String::new(),
            model_name: "gpt2".to_string(),
            tokenizer_name: None,
            max_vus: 128,
            duration_secs: 120,
            rate: None,
            warmup_secs: 30,
            benchmark_kind: "throughput".to_string(),
            num_rates: 10,
            rates: None,
        }
    }
}

/// Request template for generating requests
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestTemplate {
    /// Request ID
    pub id: String,
    /// Prompt text
    pub prompt: String,
    /// Number of prompt tokens
    pub num_prompt_tokens: u64,
    /// Target decode tokens (optional)
    pub num_decode_tokens: Option<u64>,
}

// ============================================================================
// Coordinator Messages
// ============================================================================

/// Start a benchmark run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartBenchmark {
    pub config: BenchmarkConfig,
    pub run_id: String,
}

/// Stop the current benchmark
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StopBenchmark {
    pub run_id: String,
    pub reason: String,
}

/// Benchmark phase transition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhaseTransition {
    pub run_id: String,
    pub phase: BenchmarkPhase,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BenchmarkPhase {
    Initializing,
    Warmup,
    Running,
    Cooldown,
    Completed,
    Failed(String),
}

/// Coordinator status response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoordinatorStatus {
    pub run_id: Option<String>,
    pub phase: Option<BenchmarkPhase>,
    pub workers: u32,
    pub active_requests: u64,
}

// ============================================================================
// Scheduler Messages
// ============================================================================

/// Configure the scheduler
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigureScheduler {
    pub scheduler_type: SchedulerType,
    pub max_vus: u64,
    pub duration_secs: u64,
    pub rate: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub enum SchedulerType {
    /// Constant number of virtual users
    #[default]
    ConstantVUs,
    /// Constant arrival rate
    ConstantArrivalRate,
}

/// Start scheduling requests
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartScheduling {
    pub phase_id: String,
}

/// Pause scheduling
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PauseScheduling;

/// Resume scheduling
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResumeScheduling;

/// Scheduler progress update (sent to Coordinator)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchedulerProgress {
    pub phase_id: String,
    pub progress_pct: f64,
    pub sent_requests: u64,
    pub active_vus: u64,
    pub elapsed_secs: f64,
}

// ============================================================================
// Worker Messages
// ============================================================================

/// Send a request (from Scheduler to Worker)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SendRequest {
    pub request_id: String,
    pub template: RequestTemplate,
    pub target_url: String,
    pub api_key: String,
    pub model_name: String,
}

/// Request completed (from Worker to Collector)
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RequestCompleted {
    pub request_id: String,
    pub success: bool,
    pub error: Option<String>,
    /// Time to first token in milliseconds
    pub ttft_ms: Option<f64>,
    /// Total latency in milliseconds
    pub latency_ms: f64,
    /// Number of generated tokens
    pub generated_tokens: u64,
    /// Number of prompt tokens
    pub prompt_tokens: u64,
    /// Time per output token in milliseconds
    pub tpot_ms: Option<f64>,
    /// Token timestamps for detailed analysis
    pub token_times_ms: Vec<f64>,
}

/// Worker ready notification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerReady {
    pub worker_id: String,
}

/// Worker status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkerStatus {
    pub worker_id: String,
    pub active_requests: u32,
    pub completed_requests: u64,
    pub failed_requests: u64,
}

// ============================================================================
// Collector Messages
// ============================================================================

/// Register a new run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterRun {
    pub run_id: String,
    pub config: BenchmarkConfig,
}

/// Start a new phase
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartPhase {
    pub run_id: String,
    pub phase_id: String,
    pub phase_name: String,
    pub scheduler_type: SchedulerType,
    pub target_rate: Option<f64>,
}

/// End current phase
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EndPhase {
    pub run_id: String,
    pub phase_id: String,
}

/// Get current metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GetMetrics {
    pub run_id: String,
}

/// Get final report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GetReport {
    pub run_id: String,
}

/// Real-time metrics snapshot
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MetricsSnapshot {
    pub phase_id: String,
    pub phase_name: String,
    pub progress_pct: f64,
    pub elapsed_secs: f64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub request_rate: f64,
    pub avg_ttft_ms: Option<f64>,
    pub avg_tpot_ms: Option<f64>,
    pub ttft_std_ms: Option<f64>,
    pub tpot_std_ms: Option<f64>,
    pub avg_latency_ms: Option<f64>,
    pub p50_latency_ms: Option<f64>,
    pub p95_latency_ms: Option<f64>,
    pub p99_latency_ms: Option<f64>,
    pub input_throughput: Option<f64>,
    pub output_throughput: Option<f64>,
    pub total_throughput: Option<f64>,
}

/// Final benchmark report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkReport {
    pub run_id: String,
    pub config: BenchmarkConfig,
    pub phases: Vec<PhaseReport>,
    pub start_time: String,
    pub end_time: String,
    pub total_duration_secs: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhaseReport {
    pub phase_id: String,
    pub phase_name: String,
    pub duration_secs: f64,
    pub metrics: MetricsSnapshot,
}

// ============================================================================
// Common Response Messages
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AckMessage {
    pub success: bool,
    pub message: String,
}

impl AckMessage {
    pub fn ok() -> Self {
        Self {
            success: true,
            message: "OK".to_string(),
        }
    }

    pub fn error(msg: impl Into<String>) -> Self {
        Self {
            success: false,
            message: msg.into(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_benchmark_config_default() {
        let config = BenchmarkConfig::default();
        assert_eq!(config.url, "http://localhost:8000");
        assert_eq!(config.model_name, "gpt2");
        assert_eq!(config.max_vus, 128);
        assert_eq!(config.duration_secs, 120);
        assert_eq!(config.warmup_secs, 30);
        assert!(config.rate.is_none());
        assert_eq!(config.benchmark_kind, "throughput");
    }

    #[test]
    fn test_benchmark_config_serialization() {
        let config = BenchmarkConfig {
            url: "http://test.com".to_string(),
            api_key: "key".to_string(),
            model_name: "model".to_string(),
            tokenizer_name: Some("tokenizer".to_string()),
            max_vus: 10,
            duration_secs: 60,
            rate: Some(5.0),
            warmup_secs: 10,
            benchmark_kind: "rate".to_string(),
            num_rates: 5,
            rates: Some(vec![1.0, 2.0]),
        };

        let json = serde_json::to_string(&config).unwrap();
        let deserialized: BenchmarkConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.url, config.url);
        assert_eq!(deserialized.rate, Some(5.0));
        assert_eq!(deserialized.rates, Some(vec![1.0, 2.0]));
    }

    #[test]
    fn test_request_template() {
        let template = RequestTemplate {
            id: "req-1".to_string(),
            prompt: "Hello world".to_string(),
            num_prompt_tokens: 2,
            num_decode_tokens: Some(100),
        };

        assert_eq!(template.id, "req-1");
        assert_eq!(template.num_prompt_tokens, 2);
        assert_eq!(template.num_decode_tokens, Some(100));
    }

    #[test]
    fn test_ack_message_ok() {
        let ack = AckMessage::ok();
        assert!(ack.success);
        assert_eq!(ack.message, "OK");
    }

    #[test]
    fn test_ack_message_error() {
        let ack = AckMessage::error("Something went wrong");
        assert!(!ack.success);
        assert_eq!(ack.message, "Something went wrong");
    }

    #[test]
    fn test_ack_message_error_string() {
        let error_msg = String::from("Error from string");
        let ack = AckMessage::error(error_msg);
        assert!(!ack.success);
        assert_eq!(ack.message, "Error from string");
    }

    #[test]
    fn test_benchmark_phase_equality() {
        assert_eq!(BenchmarkPhase::Initializing, BenchmarkPhase::Initializing);
        assert_eq!(BenchmarkPhase::Warmup, BenchmarkPhase::Warmup);
        assert_eq!(BenchmarkPhase::Running, BenchmarkPhase::Running);
        assert_eq!(BenchmarkPhase::Cooldown, BenchmarkPhase::Cooldown);
        assert_eq!(BenchmarkPhase::Completed, BenchmarkPhase::Completed);
        assert_ne!(BenchmarkPhase::Running, BenchmarkPhase::Completed);
    }

    #[test]
    fn test_benchmark_phase_failed() {
        let failed = BenchmarkPhase::Failed("Connection error".to_string());
        if let BenchmarkPhase::Failed(msg) = failed {
            assert_eq!(msg, "Connection error");
        } else {
            panic!("Expected Failed variant");
        }
    }

    #[test]
    fn test_scheduler_type_default() {
        let scheduler_type = SchedulerType::default();
        assert_eq!(scheduler_type, SchedulerType::ConstantVUs);
    }

    #[test]
    fn test_scheduler_type_equality() {
        assert_eq!(SchedulerType::ConstantVUs, SchedulerType::ConstantVUs);
        assert_eq!(
            SchedulerType::ConstantArrivalRate,
            SchedulerType::ConstantArrivalRate
        );
        assert_ne!(SchedulerType::ConstantVUs, SchedulerType::ConstantArrivalRate);
    }

    #[test]
    fn test_request_completed_default() {
        let completed = RequestCompleted::default();
        assert!(completed.request_id.is_empty());
        assert!(!completed.success);
        assert!(completed.error.is_none());
        assert!(completed.ttft_ms.is_none());
        assert_eq!(completed.latency_ms, 0.0);
        assert_eq!(completed.generated_tokens, 0);
        assert_eq!(completed.prompt_tokens, 0);
        assert!(completed.tpot_ms.is_none());
        assert!(completed.token_times_ms.is_empty());
    }

    #[test]
    fn test_request_completed_success() {
        let completed = RequestCompleted {
            request_id: "req-123".to_string(),
            success: true,
            error: None,
            ttft_ms: Some(50.0),
            latency_ms: 500.0,
            generated_tokens: 100,
            prompt_tokens: 10,
            tpot_ms: Some(4.5),
            token_times_ms: vec![50.0, 54.5, 59.0],
        };

        assert!(completed.success);
        assert_eq!(completed.ttft_ms, Some(50.0));
        assert_eq!(completed.latency_ms, 500.0);
    }

    #[test]
    fn test_metrics_snapshot_default() {
        let snapshot = MetricsSnapshot::default();
        assert!(snapshot.phase_id.is_empty());
        assert_eq!(snapshot.progress_pct, 0.0);
        assert_eq!(snapshot.successful_requests, 0);
        assert!(snapshot.avg_ttft_ms.is_none());
    }

    #[test]
    fn test_coordinator_status() {
        let status = CoordinatorStatus {
            run_id: Some("run-123".to_string()),
            phase: Some(BenchmarkPhase::Running),
            workers: 4,
            active_requests: 10,
        };

        assert_eq!(status.run_id, Some("run-123".to_string()));
        assert_eq!(status.workers, 4);
        assert_eq!(status.active_requests, 10);
    }

    #[test]
    fn test_start_benchmark() {
        let config = BenchmarkConfig::default();
        let start = StartBenchmark {
            config: config.clone(),
            run_id: "test-run".to_string(),
        };

        assert_eq!(start.run_id, "test-run");
        assert_eq!(start.config.url, config.url);
    }

    #[test]
    fn test_stop_benchmark() {
        let stop = StopBenchmark {
            run_id: "test-run".to_string(),
            reason: "User interrupted".to_string(),
        };

        assert_eq!(stop.run_id, "test-run");
        assert_eq!(stop.reason, "User interrupted");
    }

    #[test]
    fn test_configure_scheduler() {
        let config = ConfigureScheduler {
            scheduler_type: SchedulerType::ConstantArrivalRate,
            max_vus: 50,
            duration_secs: 120,
            rate: Some(10.0),
        };

        assert_eq!(config.scheduler_type, SchedulerType::ConstantArrivalRate);
        assert_eq!(config.max_vus, 50);
        assert_eq!(config.rate, Some(10.0));
    }

    #[test]
    fn test_worker_status() {
        let status = WorkerStatus {
            worker_id: "worker-1".to_string(),
            active_requests: 5,
            completed_requests: 100,
            failed_requests: 2,
        };

        assert_eq!(status.worker_id, "worker-1");
        assert_eq!(status.active_requests, 5);
        assert_eq!(status.completed_requests, 100);
        assert_eq!(status.failed_requests, 2);
    }

    #[test]
    fn test_scheduler_progress() {
        let progress = SchedulerProgress {
            phase_id: "phase-1".to_string(),
            progress_pct: 75.5,
            sent_requests: 1000,
            active_vus: 10,
            elapsed_secs: 45.0,
        };

        assert_eq!(progress.phase_id, "phase-1");
        assert_eq!(progress.progress_pct, 75.5);
        assert_eq!(progress.sent_requests, 1000);
    }

    #[test]
    fn test_benchmark_report() {
        let report = BenchmarkReport {
            run_id: "run-123".to_string(),
            config: BenchmarkConfig::default(),
            phases: vec![],
            start_time: "2024-01-01T00:00:00Z".to_string(),
            end_time: "2024-01-01T00:01:00Z".to_string(),
            total_duration_secs: 60.0,
        };

        assert_eq!(report.run_id, "run-123");
        assert_eq!(report.total_duration_secs, 60.0);
        assert!(report.phases.is_empty());
    }
}
