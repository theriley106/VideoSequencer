### README

# VideoSequencer

VideoSequencer is a Python script designed to process video files and images, extract timestamps, and rename files based on these timestamps. It uses OpenAI's API for accurate timestamp extraction from video frames.

## Features

- Extract timestamps from video frames and images
- Rename video files based on extracted timestamps
- Supports Unix timestamp formatting
- Allows cropping images to specific quadrants for more accurate timestamp extraction

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/theriley106/VideoSequencer.git
    cd VideoSequencer
    ```

2. Install the required Python packages:

    ```bash
    pip install opencv-python openai
    ```

## Usage

To use VideoSequencer, you need an OpenAI API key. You can either specify the API key directly via a command-line argument or save it in a `.api_key` file in the script's directory.

### Command-line Arguments

- `--folder`: Folder containing videos to process.
- `--api-key`: OpenAI API key.
- `--image`: Single image file to process.
- `--use-unix-timestamp`: Use Unix timestamp format (optional).
- `--quadrant`: Quadrant for cropping (1: top left, 2: top right, 3: bottom left, 4: bottom right).

### Examples

#### Processing a Folder of Videos

```bash
python VideoSequencer.py --folder /path/to/videos --api-key YOUR_OPENAI_API_KEY --use-unix-timestamp --quadrant 2
```

#### Processing a Single Image

```bash
python VideoSequencer.py --image /path/to/image.jpg --api-key YOUR_OPENAI_API_KEY --quadrant 1
```

#### Using API Key from File

Save your OpenAI API key in a file named `.api_key` in the same directory as the script. Then run the script without specifying the `--api-key` argument:

```bash
python VideoSequencer.py --folder /path/to/videos --use-unix-timestamp --quadrant 2
```