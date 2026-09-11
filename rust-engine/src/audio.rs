use crate::audio_engine::AudioConfig;

pub fn decode_frame(frame: &crate::audio_engine::AudioFrame) -> Result<Vec<f32>, tonic::Status> {
    let config = frame.config.as_ref().ok_or_else(|| {
        tonic::Status::invalid_argument("missing audio config")
    })?;

    match config.encoding.as_str() {
        "pcm_f32le" => {
            let samples: Vec<f32> = frame
                .data
                .chunks_exact(4)
                .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
                .collect();
            Ok(samples)
        }
        "pcm_i16" => {
            let samples: Vec<f32> = frame
                .data
                .chunks_exact(2)
                .map(|b| {
                    let s = i16::from_le_bytes([b[0], b[1]]);
                    s as f32 / i16::MAX as f32
                })
                .collect();
            Ok(samples)
        }
        _ => Err(tonic::Status::invalid_argument(format!(
            "unsupported encoding: {}",
            config.encoding
        ))),
    }
}

pub fn compute_energy(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return 0.0;
    }
    let sum: f32 = samples.iter().map(|s| s * s).sum();
    (sum / samples.len() as f32).sqrt()
}
