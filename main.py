import cv2
import base64
import os
import sys
import argparse
from openai import OpenAI
from datetime import datetime, timedelta
import time
import json

def to_unix_timestamp(date_string):
    # Parse the input string to a datetime object
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    
    # Convert to Unix timestamp (seconds since January 1, 1970)
    unix_timestamp = int(dt.timestamp())
    
    return unix_timestamp

def encode_image(image, quadrant):
    # Check if the input is a file path or an image array
    if isinstance(image, str):
        # If it's a file path, read the image
        image = cv2.imread(image)
    
    if image is None:
        raise ValueError("Invalid image input")

    height, width = image.shape[:2]
    if quadrant == 1:
        cropped = image[0:height//2, 0:width//2]  # Top-left quadrant
    elif quadrant == 2:
        cropped = image[0:height//2, width//2:width]  # Top-right quadrant
    elif quadrant == 3:
        cropped = image[height//2:height, 0:width//2]  # Bottom-left quadrant
    elif quadrant == 4:
        cropped = image[height//2:height, width//2:width]  # Bottom-right quadrant
    else:
        cropped = image  # Use entire image if no valid quadrant is specified
    
    # Encode the cropped image
    _, buffer = cv2.imencode('.jpg', cropped)
    return base64.b64encode(buffer).decode('utf-8')

def get_timestamp(client, base64_images):
    prompt = '''
    You are a model trained to extract UTC timestamps from video frames. You are given a series of images from a video, and you need to return the timestamp visible in each image.

    The timestamp format is "YYYY-MM-DD HH:MM:SS".

    Please return the timestamps in a JSON format as follows:
    {
        "timestamps": [
            "YYYY-MM-DD HH:MM:SS",
            "YYYY-MM-DD HH:MM:SS",
            ...
        ]
    }

    Only include the timestamps you can clearly read from the images. If you can't read a timestamp from an image, use the word "INVALID" in its place.
    '''
    
    messages = [
        {
            "role": "user",
            "content": [{
                "type": "text",
                "text": prompt
            }]
        }
    ]
    for base64_image in base64_images:
        messages[0]['content'].append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)['timestamps']

def get_video_duration(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    cap.release()
    return duration

def process_video(video_path, client, use_unix_timestamp, quadrant):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return None

    duration = get_video_duration(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_to_check = [0, frame_count // 2, frame_count - 1]  # Start, middle, end
    base64_images = []

    for frame_num in frames_to_check:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            base64_images.append(encode_image("static/invalid_frame.png", quadrant))
        else:
            base64_images.append(encode_image(frame, quadrant))

    cap.release()

    timestamps = get_timestamp(client, base64_images)

    # Convert valid timestamps to datetime objects
    valid_timestamps = []
    for i, ts in enumerate(timestamps):
        if ts != "INVALID":
            valid_timestamps.append((i, datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")))

    if not valid_timestamps:
        print(f"No valid timestamps extracted for {video_path}")
        return None

    # Determine start time based on available timestamps
    if valid_timestamps[0][0] == 0:  # Start timestamp is valid
        start_time = valid_timestamps[0][1]
    elif valid_timestamps[0][0] == 1:  # Only middle timestamp is valid
        print("Start timestamp is not valid. Trying middle.")
        start_time = valid_timestamps[0][1] - timedelta(seconds=duration / 2)
    elif valid_timestamps[0][0] == 2:  # Only end timestamp is valid
        print("Start timestamp is not valid. Trying end.")
        start_time = valid_timestamps[0][1] - timedelta(seconds=duration)
    else:
        print(f"Unexpected timestamp index for {video_path}")
        return None

    # Calculate end time by adding duration to start time
    end_time = start_time + timedelta(seconds=duration)

    start_time_str = start_time.strftime("%Y-%m-%d-%H:%M:%S")
    end_time_str = end_time.strftime("%Y-%m-%d-%H:%M:%S")

    if use_unix_timestamp:
        start_time_str = str(to_unix_timestamp(start_time_str))
        end_time_str = str(to_unix_timestamp(end_time_str))

    return start_time_str, end_time_str

def rename_video(video_path, start_time, end_time):
    directory = os.path.dirname(video_path)
    new_name = f"{start_time}__{end_time}.mp4"
    new_path = os.path.join(directory, new_name)
    # os.rename(video_path, new_path)
    print(f"Renamed {video_path} to {new_path}")

def process_videos_in_folder(folder_path, client, use_unix_timestamp, quadrant):
    for filename in os.listdir(folder_path):
        if filename.endswith('.mp4'):
            video_path = os.path.join(folder_path, filename)
            result = process_video(video_path, client, use_unix_timestamp, quadrant)
            if result:
                start_time, end_time = result
                rename_video(video_path, start_time, end_time)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process videos or images for timestamps.")
    parser.add_argument("--folder", type=str, help="Folder containing videos to process")
    parser.add_argument("--api-key", type=str, help="OpenAI API key")
    parser.add_argument("--use-unix-timestamp", action="store_true", help="Use Unix timestamp format")
    parser.add_argument("--quadrant", type=int, choices=[1, 2, 3, 4], help="Quadrant for cropping (1: top left, 2: top right, 3: bottom left, 4: bottom right)")

    args = parser.parse_args()

    api_key = args.api_key
    if args.api_key == None:
        if os.path.exists(".api_key") == False:
            raise Exception("You must either specify an open ai api key or save an api key to .api_key")
        api_key = open(".api_key").read()
    client = OpenAI(api_key=args.api_key)

    if args.folder:
        process_videos_in_folder(args.folder, client, args.use_unix_timestamp, args.quadrant)
    else:
        print("Please provide a --folder argument.")
