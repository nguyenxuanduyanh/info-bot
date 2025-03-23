# info_bot_api.py
from typing import Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
import subprocess
import json
import os
import asyncio
import logging
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("info_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("info_bot")

app = FastAPI()

class QueryModel(BaseModel):
    question: Optional[str] = None
    current_time: str
    video_id: str

async def run_query_script(command):
    """
    Run the video query script as a subprocess
    
    Args:
        command (list): Command and arguments to run
        
    Returns:
        dict: Dictionary containing returncode, stdout, and stderr
    """
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    return {
        "returncode": process.returncode,
        "stdout": stdout.decode(),
        "stderr": stderr.decode()
    }

async def get_response_from_file(file_path):
    """
    Read response from the output file
    
    Args:
        file_path (str): Path to the response file
        
    Returns:
        str or None: File content or None if file doesn't exist
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    return None

@app.post("/api/info-bot")
async def receive_data(data: QueryModel):
    """
    FastAPI endpoint that receives query data and calls the separate video_query.py script
    """
    logger.info(f"Received request: {data}")

    if data.question is None:
        data.question = "Describe the scene"
    
    # Create command to run the video_query.py script
    video_query_script = "video_query.py"  # Path to your script
    
    command = [
        "python", 
        video_query_script,
        data.video_id,
        data.current_time,
        data.question
    ]
    
    try:
        # Run the script
        logger.info(f"Running command: {' '.join(command)}")
        result = await run_query_script(command)
        
        if result["returncode"] != 0:
            logger.error(f"Script error: {result['stderr']}")
            return {
                "status": "error", 
                "message": f"Error processing video query: {result['stderr']}"
            }
        
        # Check for response file
        response_file = f"videos/{data.video_id}/{data.video_id}_query_{int(float(data.current_time))}s.txt"
        response_text = await get_response_from_file(response_file)
        
        if response_text:
            logger.info(f"Successfully processed request, response in {response_file}")
            return {
                "status": "success", 
                "message": "Query processed successfully",
                "response": response_text
            }
        else:
            logger.error(f"Response file not found: {response_file}")
            return {
                "status": "error", 
                "message": "Response file not found"
            }
    
    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        return {"status": "error", "message": f"Error: {str(e)}"}

if __name__ == "__main__":

    logger.info("Starting Info Bot API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)