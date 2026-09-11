mod audio;
mod vad;

use tonic::{transport::Server, Request, Response, Status, Streaming};

use audio_engine::audio_processor_server::{AudioProcessor, AudioProcessorServer};
use audio_engine::{AudioFrame, AudioConfig, VadResult, ProcessedChunk};

pub mod audio_engine {
    tonic::include_proto!("audio_engine");
}

struct AudioEngineService {
    vad: vad::VadDetector,
}

impl Default for AudioEngineService {
    fn default() -> Self {
        Self {
            vad: vad::VadDetector::new(),
        }
    }
}

#[tonic::async_trait]
impl AudioProcessor for AudioEngineService {
    type ProcessAudioStream = std::pin::Pin<
        Box<dyn futures_core::Stream<Item = Result<ProcessedChunk, Status>> + Send>,
    >;

    async fn process_audio(
        &self,
        request: Request<Streaming<AudioFrame>>,
    ) -> Result<Response<Self::ProcessAudioStream>, Status> {
        let mut stream = request.into_inner();
        let vad = self.vad.clone();

        let output = async_stream::stream! {
            while let Some(frame) = stream.message().await? {
                let audio_data = audio::decode_frame(&frame)?;
                let is_speech = vad.detect(&audio_data, frame.config.as_ref());
                let energy = audio::compute_energy(&audio_data);

                yield Ok(ProcessedChunk {
                    data: frame.data,
                    timestamp_ms: frame.timestamp_ms,
                    is_speech,
                    energy,
                });
            }
        };

        Ok(Response::new(Box::pin(output)))
    }

    async fn detect_voice_activity(
        &self,
        request: Request<AudioFrame>,
    ) -> Result<Response<VadResult>, Status> {
        let frame = request.into_inner();
        let audio_data = audio::decode_frame(&frame)?;
        let is_speech = self.vad.detect(&audio_data, frame.config.as_ref());

        Ok(Response::new(VadResult {
            is_speech,
            speech_probability: if is_speech { 0.95 } else { 0.05 },
            start_ms: frame.timestamp_ms,
            end_ms: frame.timestamp_ms,
        }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    let addr = "127.0.0.1:50051".parse()?;
    let service = AudioEngineService::default();

    log::info!("Audio engine listening on {}", addr);

    Server::builder()
        .add_service(AudioProcessorServer::new(service))
        .serve(addr)
        .await?;

    Ok(())
}
