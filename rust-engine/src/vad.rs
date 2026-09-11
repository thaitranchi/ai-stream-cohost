use crate::audio_engine::AudioConfig;

#[derive(Clone)]
pub struct VadDetector {
    threshold: f32,
    min_speech_ms: u64,
    last_state: bool,
}

impl Default for VadDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl VadDetector {
    pub fn new() -> Self {
        Self {
            threshold: 0.5,
            min_speech_ms: 300,
            last_state: false,
        }
    }

    pub fn detect(&mut self, samples: &[f32], config: Option<&AudioConfig>) -> bool {
        if samples.is_empty() {
            return false;
        }

        let energy = compute_rms(samples);
        let is_speech = energy > self.threshold;

        if is_speech != self.last_state {
            self.last_state = is_speech;
        }

        self.last_state
    }
}

fn compute_rms(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return 0.0;
    }
    let sum: f32 = samples.iter().map(|s| s * s).sum();
    (sum / samples.len() as f32).sqrt()
}
