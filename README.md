# WhatsApp Chat Analyzer

This project is a web application that analyzes exported WhatsApp chat files (either `.txt` or `.zip` containing a `.txt` file). It provides various statistics and visualizations about the chat.

## Features

![{F2626A01-1661-4EBC-B8D8-9E3F2C2A3E05}](https://github.com/user-attachments/assets/04cb1dd2-5fc6-4e6b-95e2-4bebcb3c67bb)
![{1BC0F20B-A1A8-4B0C-BEE7-B62BB37180E5}](https://github.com/user-attachments/assets/9145181b-a2c0-4ae2-a48f-38b3e5da8125)

## Features

- **Chat Upload**: Users can upload their WhatsApp chat export file.
- **Total Messages**: Displays the total number of messages in the chat.
- **Messages per Sender**: Shows a count of messages sent by each participant.
- **Most Common Words**: Lists the top 10 most frequently used words.
- **Most Common Emojis**: Lists the top 10 most frequently used emojis.
- **Sentiment Analysis**: Calculates and displays the average sentiment polarity for each sender.
- **Daily Activity**: Shows the volume of messages exchanged per day.
- **Busiest Day**: Identifies the day with the highest number of messages.
- **Visualizations**: Generates and displays plots for:
  - Messages per Sender
  - Daily Message Volume
  - Average Sentiment per Sender

## Technologies Used

- **Backend**: Python, FastAPI
- **Frontend**: HTML, Jinja2 Templates
- **Data Analysis**: TextBlob (for sentiment analysis), Matplotlib & Seaborn (for plotting)
- **Containerization**: Docker

## Project Structure

```
whatsapp-chat-analyzer/
├── .dockerignore
├── Dockerfile
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI application logic, routing
│   ├── static/         # Static files (CSS, JS, images)
│   │   └── plots/      # Directory where generated plots are saved
│   ├── templates/
│   │   ├── result.html   # HTML template for displaying analysis results
│   │   └── upload.html   # HTML template for the file upload form
│   ├── uploads/        # Directory where uploaded chat files are temporarily stored
│   └── utils.py        # Chat parsing, analysis functions, plot generation
└── requirements.txt    # Python dependencies
```

## Getting Started

### Prerequisites

- Docker installed (if running with Docker)
- Python 3.10+ (if running locally)

### Running with Docker

1.  **Build the Docker image:**

    ```bash
    docker build -t whatsapp-chat-analyzer .
    ```

2.  **Run the Docker container:**

    ```bash
    docker run -p 8000:8000 whatsapp-chat-analyzer
    ```

3.  Open your browser and navigate to `http://localhost:8000`.

### Running with Docker Compose (Recommended)

1.  **Run the container, modify the port if necessary:**

    ```bash
    docker-compose up -d
    ```

2.  Open your browser and navigate to `http://localhost:8000`.

### Running Locally

1.  **Clone the repository (if you haven't already):**

    ```bash
    # git clone <repository-url>
    # cd whatsapp-chat-analyzer
    ```

2.  **Create a virtual environment and activate it (optional but recommended):**

    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application using Uvicorn:**
    Navigate to the `app` directory if you are in the project root:

    ```bash
    cd app
    ```

    Then run:

    ```bash
    uvicorn main:app --reload
    ```

    If you are in the project root directory, you can run:

    ```bash
    uvicorn app.main:app --reload
    ```

5.  Open your browser and navigate to `http://localhost:8000`.

## How to Use

1.  Export your WhatsApp chat:
    - Open the WhatsApp chat you want to analyze.
    - Tap on the three dots (menu) > More > Export chat.
    - Choose 'Without Media'.
    - Save the `.txt` file (or the `.zip` file if your phone automatically zips it).
2.  Navigate to the application in your browser.
3.  Click 'Choose File', select your exported chat file, and click 'Upload'.
4.  View the analysis results and generated plots.
