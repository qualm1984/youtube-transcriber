import whisper
import torch

torch.cuda.init()
device = "cuda"

model = whisper.load_model("large", device=device)
result = model.transcribe("demis.mp3")
print(result["text"])
