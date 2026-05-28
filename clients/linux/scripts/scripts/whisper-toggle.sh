#!/bin/bash

# VoiceToText-Linux-F9: Main Toggle Script
# Читает настройки из config.yaml для гибкой конфигурации

# Configuration from config.yaml
CONFIG_FILE="/home/ai/Документы/dev/VTT-Linux/config.yaml"

# Read settings from config
WHISPER_PATH=$(grep "^whisper_path:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
MODEL_BASE_PATH=$(grep "^model_base_path:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
MODEL_NAME=$(grep "^model:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
MODEL_PATH_CONFIG=$(grep "^model_path:" "$CONFIG_FILE" | cut -d':' -f2- | sed 's/^ *//; s/"//g')
LANGUAGE=$(grep "^language:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
USE_GPU=$(grep "^use_gpu:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
CPU_THREADS=$(grep "^cpu_threads:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
MAX_CONTEXT=$(grep "^max_context:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
MAX_LEN=$(grep "^max_len:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
SAMPLE_RATE=$(grep "^sample_rate:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
CHANNELS=$(grep "^channels:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
AUDIO_FORMAT=$(grep "^audio_format:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
HOTKEY=$(grep "^hotkey:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
TEMP_DIR=$(grep "^temp_dir:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
PID_FILE=$(grep "^pid_file:" "$CONFIG_FILE" | cut -d':' -f2 | sed 's/ *//g; s/"//g')
EXTRA_PARAMS=$(grep "^extra_params:" "$CONFIG_FILE" | cut -d':' -f2- | sed 's/^ *//; s/"//g')

# Construct paths
# Determine model path with override support
if [ -n "$MODEL_PATH_CONFIG" ]; then
    MODEL_PATH="$MODEL_PATH_CONFIG"
else
    MODEL_PATH="$MODEL_BASE_PATH/ggml-${MODEL_NAME}.bin"
fi
WHISPER_BIN="$WHISPER_PATH/build-cpu/bin/whisper-cli"
RECORDING_FILE="$TEMP_DIR/recording_$(date +%Y%m%d_%H%M%S).wav"

# Create temp directory if it doesn't exist
mkdir -p "$TEMP_DIR"

# Function to show notification with icon
notify() {
    local urgency="$1"
    local message="$2"
    local icon="$3"
    
    if command -v notify-send &> /dev/null; then
        notify-send -u "$urgency" -i "$icon" "Whisper Transcription" "$message"
    fi
    echo "$message"
}

# Check if recording is already in progress
if [ -f "$PID_FILE" ]; then
    # Recording is in progress, stop it
    PID=$(cat "$PID_FILE")
    
    # Check if process is still running
    if kill -0 "$PID" 2>/dev/null; then
        # Stop recording
        kill -TERM "$PID"
        rm -f "$PID_FILE"
        
        notify "normal" "Recording stopped. Processing..." "media-playback-stop"
        
        # Wait a moment for the file to be written
        sleep 0.5
        
        # Find the most recent recording
        RECORDING_FILE=$(ls -t "$TEMP_DIR"/recording_*.wav 2>/dev/null | head -1)
        
        if [ ! -f "$RECORDING_FILE" ]; then
            notify "critical" "No recording file found!" "dialog-error"
            exit 1
        fi
        
        # Get file size
        FILE_SIZE=$(stat -c%s "$RECORDING_FILE" 2>/dev/null || stat -f%z "$RECORDING_FILE" 2>/dev/null)
        if [ "$FILE_SIZE" -lt 1000 ]; then
            notify "critical" "Recording too short!" "dialog-warning"
            rm "$RECORDING_FILE"
            exit 1
        fi
        
        # Transcribe the audio
        notify "normal" "Transcribing audio..." "applications-multimedia"

        export LD_LIBRARY_PATH="$WHISPER_PATH/build-cpu/src:$WHISPER_PATH/build-cpu/ggml/src:$LD_LIBRARY_PATH"

        # Build whisper-cli command with dynamic parameters
        CMD="$WHISPER_BIN -m \"$MODEL_PATH\" -f \"$RECORDING_FILE\""

        # Add GPU parameters if enabled
        if [ "$USE_GPU" = "true" ]; then
            CMD="$CMD --gpu"
            notify "normal" "Using GPU acceleration..." "applications-multimedia"
        else
            notify "normal" "Using CPU processing..." "applications-multimedia"

            if [ -n "$CPU_THREADS" ]; then
                if [[ "$CPU_THREADS" =~ ^[0-9]+$ ]] && [ "$CPU_THREADS" -gt 0 ]; then
                    CMD="$CMD --threads $CPU_THREADS"
                    notify "normal" "CPU threads: $CPU_THREADS" "preferences-system-performance"
                else
                    notify "critical" "Invalid cpu_threads value: $CPU_THREADS" "dialog-warning"
                fi
            fi
        fi

        # Add language settings
        if [ "$LANGUAGE" = "auto" ]; then
            CMD="$CMD --language auto"
        else
            CMD="$CMD --language $LANGUAGE"
        fi

        # Add context and length limits
        if [ "$MAX_CONTEXT" != "0" ]; then
            CMD="$CMD --max-context $MAX_CONTEXT"
        fi

        if [ "$MAX_LEN" != "0" ]; then
            CMD="$CMD --max-len $MAX_LEN"
        fi

        # Add extra parameters and threading
        CMD="$CMD $EXTRA_PARAMS -nt"

        # Debug: show command being executed
        echo "Debug CMD: $CMD" >> /tmp/whisper-debug.log

        # Execute transcription
        TRANSCRIPTION=$(eval "$CMD 2>&1" | grep -v "whisper_" | grep -v "main:" | grep -v "system_info:" | grep -v "^$" | sed 's/^[[:space:]]*//' | tr -d '\n')
        
        # Check if transcription was successful
        if [ -z "$TRANSCRIPTION" ]; then
            notify "critical" "Transcription failed!" "dialog-error"
            exit 1
        fi
        
        # Copy to clipboard
        if command -v xclip &> /dev/null; then
            echo -n "$TRANSCRIPTION" | xclip -selection clipboard
            notify "normal" "Transcription copied to clipboard!" "edit-paste"
        elif command -v xsel &> /dev/null; then
            echo -n "$TRANSCRIPTION" | xsel --clipboard --input
            notify "normal" "Transcription copied to clipboard!" "edit-paste"
        else
            notify "normal" "Transcription complete (no clipboard tool found)" "dialog-information"
        fi
        
        # Save transcription to file
        TRANSCRIPT_FILE="$TEMP_DIR/transcript_$(date +%Y%m%d_%H%M%S).txt"
        echo "$TRANSCRIPTION" > "$TRANSCRIPT_FILE"
        
        # Show transcription in notification
        PREVIEW=$(echo "$TRANSCRIPTION" | head -c 100)
        if [ ${#TRANSCRIPTION} -gt 100 ]; then
            PREVIEW="${PREVIEW}..."
        fi
        notify "normal" "Transcription: $PREVIEW" "text-x-generic"
        
        # Clean up old recordings (keep last 10)
        ls -t "$TEMP_DIR"/recording_*.wav 2>/dev/null | tail -n +11 | xargs -r rm
        ls -t "$TEMP_DIR"/transcript_*.txt 2>/dev/null | tail -n +11 | xargs -r rm
    else
        # Process not running, clean up PID file
        rm -f "$PID_FILE"
        notify "normal" "No recording in progress" "dialog-information"
    fi
else
    # No recording in progress, start one
    notify "normal" "Recording started... Press F9 again to stop" "media-record"
    
    # Start recording in background
    RECORDING_FILE="$TEMP_DIR/recording_$(date +%Y%m%d_%H%M%S).wav"
    arecord -f S16_LE -r 16000 -c 1 "$RECORDING_FILE" 2>/dev/null &
    
    # Save PID
    echo $! > "$PID_FILE"
fi