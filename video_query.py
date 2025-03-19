import os
import argparse
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def find_scene_for_timestamp(scene_info, timestamp):
    """Find the scene containing the specified timestamp"""
    for scene in scene_info:
        if scene["start_time"] <= timestamp < scene["end_time"]:
            return scene
    return None

def get_context_from_previous_scene(scene_info, current_scene):
    """Get context from the previous scene if available"""
    current_index = current_scene["scene_number"] - 1  # Adjust for 0-based indexing
    if current_index > 0:
        return scene_info[current_index - 1]  # Get previous scene
    return None

def format_transcript(transcript_list):
    """Format transcript list into readable text"""
    if not transcript_list:
        return "No transcript available."
    
    return "\n".join([f"[{t.get('start', 0):.2f}s - {t.get('end', 0):.2f}s]: {t.get('text', '')}" 
                     for t in transcript_list])

def format_captions(captions_list):
    """Format captions list into readable text"""
    if not captions_list:
        return "No captions available."
    
    return "\n".join([f"[{c.get('start', 0):.2f}s - {c.get('end', 0):.2f}s]: {c.get('text', '')}" 
                     for c in captions_list])

def query_video_scene_with_api(video_id, timestamp, query):
    """Query a specific video scene using the Qwen2.5-VL-72B API"""
    # Load scene info
    scene_info_path = f"videos/{video_id}/{video_id}_scenes_new/scene_info.json"
    print(scene_info_path)
    try:
        with open(scene_info_path, "r") as f:
            scene_info = json.load(f)
    except FileNotFoundError:
        print(f"Error: Scene info file not found at {scene_info_path}")
        return "Scene information not found for this video."
    
    # Find the scene containing the timestamp
    scene = find_scene_for_timestamp(scene_info, timestamp)
    if not scene:
        print(f"Error: No scene found for timestamp {timestamp}")
        return f"No scene was found for timestamp {timestamp}s in this video."
    
    # Get previous scene for context
    prev_scene = get_context_from_previous_scene(scene_info, scene)
    
    # Get scene path and ensure it exists
    scene_path = scene.get("scene_path", "")
    if not os.path.exists(scene_path):
        print(f"Error: Scene video not found at {scene_path}")
        return f"Video file for scene {scene['scene_number']} not found."
    
    # Convert video for Qwen if needed
    '''
    try:
        print(f"Converting video for Qwen compatibility...")
        qwen_video_path = convert_for_qwen(scene_path)
    except Exception as e:
        print(f"Error converting video: {str(e)}")
        return f"Error preparing video for analysis: {str(e)}"
    '''

    # Prepare context information
    scene_info_text = (
        f"SCENE NUMBER: {scene['scene_number']}\n"
        f"TIMESTAMP RANGE: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s\n"
        f"DURATION: {scene['duration']:.2f}s\n"
        f"QUERY TIMESTAMP: {timestamp}s (within this scene)\n\n"
    )
    
    # Add scene transcript
    scene_info_text += "SCENE TRANSCRIPT:\n"
    scene_info_text += format_transcript(scene.get("transcript", [])) + "\n\n"
    
    # Add scene captions
    scene_info_text += "SCENE CAPTIONS:\n"
    scene_info_text += format_captions(scene.get("captions", [])) + "\n\n"
    
    # Add previous scene context if available
    if prev_scene:
        scene_info_text += "PREVIOUS SCENE INFORMATION:\n"
        scene_info_text += f"SCENE NUMBER: {prev_scene['scene_number']}\n"
        scene_info_text += f"TIMESTAMP RANGE: {prev_scene['start_time']:.2f}s - {prev_scene['end_time']:.2f}s\n"
        scene_info_text += "TRANSCRIPT:\n"
        scene_info_text += format_transcript(prev_scene.get("transcript", [])) + "\n"
        scene_info_text += "CAPTIONS:\n"
        scene_info_text += format_captions(prev_scene.get("captions", [])) + "\n\n"
    
    # Create prompt with context and query
    prompt = f"""
    VIDEO SCENE CONTEXT:
    {scene_info_text}
    
    USER QUERY:
    {query}
    
    Please analyze the video scene and respond to the user's query.
    Focus on what is visible and happening at timestamp {timestamp}s (within this scene),
    considering both visual content and available transcript/captions.
    """
    
    # Read and encode the video
    with open(scene_path, "rb") as video_file:
        encoded_video = base64.b64encode(video_file.read()).decode('utf-8')
    
    # Initialize the API client
    client = OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    
    # Call the API
    try:
        completion = client.chat.completions.create(
            model="qwen2.5-vl-72b-instruct",
            messages=[
                {"role": "system", "content": "You analyze video content and answer specific questions about it."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{encoded_video}"}}
                ]}
            ],
            max_tokens=2000
        )
        
        # Extract response
        response = completion.choices[0].message.content
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error calling API: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Video Scene Query Tool using Qwen2.5-VL-72B API")
    parser.add_argument("video_id", help="ID of the video (e.g., '_1DDhUnyvwY')")
    parser.add_argument("timestamp", type=float, help="Timestamp in seconds to query about")
    parser.add_argument("query", help="Question about what's happening at the timestamp")
    
    args = parser.parse_args()
    
    # Process the query
    response = query_video_scene_with_api(args.video_id, args.timestamp, args.query)
    
    print("\n=== RESPONSE ===\n")
    print(response)
    
    # Save response to file
    output_file = f"{args.video_id}_query_{int(args.timestamp)}s.txt"
    with open(output_file, "w") as f:
        f.write(response)
    print(f"\nResponse saved to {output_file}")

if __name__ == "__main__":
    main()