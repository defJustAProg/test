from typing import Annotated
from fastapi import FastAPI, Query, UploadFile, File
import os
from dotenv import load_dotenv
import json
from datetime import date
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import httpx
from fastapi.responses import JSONResponse
from vosk import Model, KaldiRecognizer, SetLogLevel
from pydub import AudioSegment
import vosk
import pydub
import wave

app = FastAPI()
load_dotenv()

FRAME_RATE = 16000 # Нужная частота дискретизации
CHANNELS = 1 # Нужное количество каналов

model = Model(model_path=r'C:\Users\Admin\Desktop\warehouse\server\models\vosk-model-ru-0.42\vosk-model-ru-0.42')

@app.put("/transcribe")
async def transcribe(file: UploadFile):
    try:
        
         # Временные файлы для хранения аудио
        temp_mp3_path = 'temp_audio.mp3'

        # Сохраняем загруженный MP3 файл
        with open(temp_mp3_path, "wb") as temp_file:
            temp_file.write(await file.read())

        # Конвертируем MP3 в WAV
        audio = pydub.AudioSegment.from_mp3(temp_mp3_path)
        with open("temp.wav", mode="wb") as temp_file:
            audio.export(out_f=temp_file, format="wav")

        # Открытие аудиофайла wav
        wf = wave.open('temp.wav', "rb")
        rec = KaldiRecognizer(model, wf.getframerate())

        # Открываем WAV файл для транскрипции
        with open("temp.wav", "rb") as wav_file:
            rec.AcceptWaveform(wav_file.read())
            result = rec.Result()
            text = json.loads(result)["text"]
            print(text)

        async with httpx.AsyncClient() as client:
            await client.post(os.getenv('CLIENT_HOST'), json=result)
            return JSONResponse(content={"message": "ok"}, status_code=200)
        
    except Exception as e:
        print('Ошибка транскрибации:', e)
    except httpx.HTTPStatusError:
        return JSONResponse(content={"message": "error"}, status_code=503)
    
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv('SERVER_HOST'), port=int(os.getenv('SERVER_PORT',8000)))# default=8000