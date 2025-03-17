from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

class QueryModel(BaseModel):
    question: str
    current_time: str
    video_id: str

@app.post("/api/info-bot")
async def receive_data(data: QueryModel):
    # TODO: Custom a promt for the model
    print(data)
    return {"message": "Data received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)