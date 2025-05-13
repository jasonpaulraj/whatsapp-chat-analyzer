from collections import Counter, defaultdict
import re
from datetime import datetime
from pathlib import Path
import emoji
from textblob import TextBlob
import shutil # Added for file copying
# Matplotlib and Seaborn removed for client-side plotting
import os # Retained for os.makedirs if needed elsewhere, or can be removed if not used by other functions.
attachment_regex = re.compile(r'^\u200e?<attached: (.*?)>')
sentence_end_regex = re.compile(r'[.!?]+')
def parse_chat(file_path: Path):
    """Parses a WhatsApp chat file and extracts messages, timestamps, senders, and media attachment info."""
    messages = []
    # Regex to match lines like: [19/01/2025, 10:59:54 AM] JP: Eh  
    # Or attachment lines: \u200e[19/01/2025, 10:59:54 AM] JP: \u200e<attached: file.jpg>
    # The initial \u200e is optional. The one before <attached...> is also optional.
    line_regex = re.compile(r'^\u200e?\[(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}:\d{2}\s*[APM]{2})\] (.*?): (.*)')
    

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_match = line_regex.match(line)
            if line_match:
                date_str, time_str, sender, message_content = line_match.groups()
                media_filename = None
                media_type = None

                # Check if the message content is an attachment
                attachment_match = attachment_regex.match(message_content)
                if attachment_match:
                    media_filename = attachment_match.group(1)
                    message_content = f"<{media_filename}>" # Replace message with a placeholder like <file.jpg>
                    # Determine media type from extension
                    ext = media_filename.split('.')[-1].lower() if '.' in media_filename else ''
                    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                        media_type = 'image'
                    elif ext in ['mp4', 'mov', 'avi', 'mkv', '3gp']:
                        media_type = 'video'
                    elif ext in ['mp3', 'wav', 'ogg', 'opus', 'aac', 'm4a']:
                        media_type = 'audio'
                    # 'webp' can also be stickers, but WhatsApp often names sticker files with STICKER in them.
                    # We can refine this later if needed, or rely on filename conventions.
                    if 'sticker' in media_filename.lower() and ext == 'webp':
                         media_type = 'sticker'
                
                try:
                    timestamp = datetime.strptime(f"{date_str} {time_str.strip()}", "%d/%m/%Y %I:%M:%S %p")
                except ValueError as e:
                    print(f"Error parsing timestamp: {date_str} {time_str} - {e}")
                    continue
                
                messages.append({
                    "timestamp": timestamp,
                    "sender": sender,
                    "message": message_content,
                    "media_filename": media_filename,
                    "media_type": media_type
                })
            # Handle multi-line messages (append to the previous message if sender and timestamp match)
            # This is a simplified approach; robust multi-line handling can be complex.
            elif messages and line.strip(): # if not a new message line and not empty
                # Heuristic: if a line doesn't match the pattern and the previous message exists,
                # append it to the previous message's content.
                # This might need refinement for very specific chat export formats.
                messages[-1]["message"] += "\n" + line.strip()

    return messages


def get_top_sentences(messages, top_n=10):
    """Extracts and counts sentences from messages, returning the most common ones."""
    sentence_counts = Counter()
    for msg_data in messages:
        # Only process actual text messages, ignore media placeholders for sentence analysis
        if not msg_data.get("media_type"):
            # Normalize: lowercase, strip whitespace
            text = msg_data["message"].lower().strip()
            # Split into sentences based on '.', '!', '?'
            # Filter out very short "sentences" (e.g., just punctuation or single words if desired)
            sentences = [s.strip() for s in sentence_end_regex.split(text) if len(s.strip().split()) > 2] # Min 3 words
            sentence_counts.update(sentences)
    return sentence_counts.most_common(top_n)

# generate_plots function removed as plotting will be handled client-side.

def analyze_chat(file_path: Path, media_options: str = "analyze_media", media_folder_path: str = None, static_previews_dir: Path = None, session_id: str = None):
    """Analyzes chat messages for various metrics, including media attachments."""
    
    messages = parse_chat(file_path)
    if not messages:
        return {"error": "No messages found."}

    total_msgs = len(messages)
    senders = Counter(msg["sender"] for msg in messages)

    word_counts = Counter()
    emoji_counts = Counter()
    sentiment_scores = defaultdict(list)
    daily_activity = Counter() 
    hourly_activity = Counter() 
    day_of_week_activity = Counter() 
    message_lengths_per_sender = defaultdict(list)
    link_counts_per_sender = defaultdict(int)
    question_counts_per_sender = defaultdict(int)
    media_counts_per_sender = defaultdict(lambda: Counter()) # sender -> media_type -> count
    total_media_counts = Counter() # media_type -> count
    total_links = 0
    total_questions = 0

    for msg in messages:
        # Standard message analysis
        words = msg["message"].split()
        # Exclude attachment placeholders like '<file.jpg>' from word counts if desired
        # For now, they are included, which might be okay or might need filtering.
        word_counts.update(w for w in words if not attachment_regex.match(w)) # Filter out attachment placeholders
        emoji_counts.update(c for c in msg["message"] if c in emoji.EMOJI_DATA)
        
        # Sentiment analysis only on non-attachment messages or a placeholder text
        text_for_sentiment = msg["message"]
        if msg["media_type"]:
            text_for_sentiment = f"Sent a {msg['media_type']}" # Generic text for media sentiment

        polarity = TextBlob(text_for_sentiment).sentiment.polarity
        sentiment_scores[msg["sender"]].append(polarity)
        
        daily_activity[msg["timestamp"].date()] += 1
        hourly_activity[msg["timestamp"].hour] += 1
        day_of_week_activity[msg["timestamp"].weekday()] += 1
        message_lengths_per_sender[msg["sender"]].append(len(msg["message"])) # Length of placeholder for media

        if re.search(r'https?://\S+', msg["message"]):
            link_counts_per_sender[msg["sender"]] += 1
            total_links += 1
        
        if msg["message"].strip().endswith('?') and not msg["media_type"]:
            question_counts_per_sender[msg["sender"]] += 1
            total_questions += 1

        # Media analysis
        # The media_options string from the form determines behavior.
        # 'analyze_media': analyze, show full previews
        # 'analyze_media_no_preview': analyze, show no previews
        # 'analyze_media_shrink_preview': analyze, show shrinked (not implemented yet, treat as full for now)
        if media_options != "text_only": # Assuming 'text_only' could be an option to ignore media entirely
            if msg["media_type"]:
                media_counts_per_sender[msg["sender"]][msg["media_type"]] += 1
                total_media_counts[msg["media_type"]] += 1

    most_common_words = word_counts.most_common(10)
    most_common_emojis = emoji_counts.most_common(10)
    top_sentences = get_top_sentences(messages, top_n=10)
    avg_sentiment = {sender: round(sum(scores)/len(scores), 3) if scores else 0 for sender, scores in sentiment_scores.items()}
    avg_message_length_per_sender = {sender: round(sum(lengths)/len(lengths), 1) if lengths else 0 for sender, lengths in message_lengths_per_sender.items()}

    busiest_day_tuple = max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else (None, 0)
    busiest_day = {
        "date": str(busiest_day_tuple[0]) if busiest_day_tuple[0] else "N/A",
        "message_count": busiest_day_tuple[1]
    }

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_of_week_activity_named = {day_names[day_num]: count for day_num, count in sorted(day_of_week_activity.items())}
    hourly_activity_sorted = {hour: count for hour, count in sorted(hourly_activity.items())}

    serializable_sample_messages = []
    show_previews = media_options not in ["analyze_media_no_preview"]

    for msg_data in messages[-500:]: # Show more sample messages, including media
        serializable_msg = {
            "timestamp": msg_data["timestamp"].isoformat(),
            "sender": msg_data["sender"],
            "message": msg_data["message"],
            "media_type": msg_data["media_type"],
            "media_filename": msg_data["media_filename"],
            "media_preview_path": None # Initialize
        }

        if show_previews and msg_data["media_filename"] and media_folder_path and static_previews_dir:
            source_media_path = Path(media_folder_path) / msg_data["media_filename"]
            preview_filename = msg_data["media_filename"]
            # Sanitize filename if necessary, or ensure it's unique if multiple zips are processed.
            # For now, using original filename.
            destination_preview_path_abs = static_previews_dir / preview_filename

            if source_media_path.exists():
                try:
                    static_previews_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_media_path, destination_preview_path_abs)
                    # Construct path relative to static dir, including session_id
                    serializable_msg["media_preview_path"] = f"media_previews/{session_id}/{preview_filename}"
                except Exception as e:
                    print(f"Error copying media for preview {preview_filename}: {e}")
                    serializable_msg["media_preview_path"] = None # Fallback if copy fails
            else:
                # print(f"Source media file not found for preview: {source_media_path}")
                pass # Keep media_preview_path as None
        
        serializable_sample_messages.append(serializable_msg)

    result = {
        "total_messages": total_msgs,
        "messages_per_sender": dict(senders),
        "most_common_words": most_common_words,
        "most_common_emojis": most_common_emojis,
        "average_sentiment": avg_sentiment,
        "busiest_day": busiest_day,
        "daily_activity": {str(k): v for k, v in sorted(daily_activity.items())},
        "hourly_activity": hourly_activity_sorted,
        "day_of_week_activity": day_of_week_activity_named,
        "avg_message_length_per_sender": avg_message_length_per_sender,
        "link_counts_per_sender": dict(link_counts_per_sender),
        "question_counts_per_sender": dict(question_counts_per_sender),
        "total_links": total_links,
        "total_questions": total_questions,
        "media_counts_per_sender": {s: dict(counts) for s, counts in media_counts_per_sender.items()},
        "total_media_counts": dict(total_media_counts),
        "total_media_count": sum(total_media_counts.values()), # Added total count of all media
        "top_sentences": top_sentences, # Added top sentences
        "sample_messages": serializable_sample_messages,
        "media_options_used": media_options # Pass along the options used for analysis, renamed for clarity
    }

    return result
