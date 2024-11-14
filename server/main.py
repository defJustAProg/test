from fastapi import FastAPI, UploadFile, File
import os
from dotenv import load_dotenv
import json
import httpx
from fastapi.responses import JSONResponse
from vosk import Model, KaldiRecognizer, SetLogLevel
import vosk
import pydub
import wave
from pydantic import BaseModel

app = FastAPI()
load_dotenv()

class PathBodyScheme(BaseModel):
    PATH: str

FRAME_RATE = 16000 # Нужная частота дискретизации
CHANNELS = 1 # Нужное количество каналов

model = Model(model_path=os.getenv('MODEL_PATH'))

async def transcribe(file: UploadFile):
    try:

        # Сохраняем загруженный MP3 файл
        async with open('temp_audio.mp3', "wb") as temp_file:
            await temp_file.write(await file.read())

        # Конвертируем MP3 в WAV
        audio = pydub.AudioSegment.from_mp3('temp_audio.mp3')
        async with open('temp.wav', mode="wb") as temp_file:
            await audio.export(out_f=temp_file, format="wav")

        # Открытие аудиофайла wav
        wf = wave.open('temp.wav', "rb")
        rec = KaldiRecognizer(model, wf.getframerate())

        # Открываем WAV файл для транскрипции
        async with open("temp.wav", "rb") as wav_file:
            rec.AcceptWaveform(wav_file.read())
            result = rec.Result()
            text = json.loads(result)["text"]
            print(text)

        os.remove('temp_audio.mp3')
        os.remove('temp.wav')

    except Exception as e:
        print('Ошибка транскрибации:', e)
        return JSONResponse(content={"error": "transcribation error"}, status_code=500)
    
    return text


@app.put("/transcribe_by_path")
async def transcribe_file_by_path(pathBodyScheme: PathBodyScheme):
    
    async with open(pathBodyScheme.PATH, "rb") as file:
        text = await transcribe(file)
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(os.getenv('CLIENT_HOST'), json={'text': text})
            return JSONResponse(content={"message": "ok"}, status_code=200)
        
    except httpx.HTTPStatusError:
        return JSONResponse(content={"message": f"error request to {os.getenv('CLIENT_HOST')}"}, status_code=503)
    

@app.put("/transcribe_file")
async def transcribe(file: UploadFile = File(...)):
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(os.getenv('CLIENT_HOST'), json={'text': await transcribe(file)})
            return JSONResponse(content={"message": "ok"}, status_code=200)
        
    except httpx.HTTPStatusError:
        return JSONResponse(content={"message": f"error request to {os.getenv('CLIENT_HOST')}"}, status_code=503)
    
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv('SERVER_HOST'), port=int(os.getenv('SERVER_PORT',8000)))# default=8000