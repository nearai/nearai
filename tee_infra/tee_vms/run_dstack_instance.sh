if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Error: DATA_DIR and YAML_FILE parameters are required"
    echo "Usage: $0 <data_dir> <yaml_file> [file_to_copy]"
    exit 1
fi
DATA_DIR="$1"
YAML_FILE="$2"
FILE_TO_COPY="$3"

# Check if the YAML file exists
if [ ! -f "$YAML_FILE" ]; then
    echo "Error: YAML file '$YAML_FILE' not found"
    exit 1
fi

DIR_NAME=$(basename "$YAML_FILE" .yaml)
PRIVATE_ML_SDK_DIR="/home/ubuntu/private-ml-sdk"

rm -rf $DATA_DIR/$DIR_NAME

echo "Creating dstack instance..."
# Run dstack new and check for failure
dstack new $YAML_FILE -o $DATA_DIR/$DIR_NAME --image $PRIVATE_ML_SDK_DIR/images/dstack-dev-0.3.5/ -c 12 -m 32G -d 2T --port tcp:20022:22 --port tcp:0.0.0.0:4433:443
if [ $? -ne 0 ]; then
    echo "Error: Failed to create dstack instance"
    exit 1
fi

# Copy the specified file to data_dir/DIR_NAME/shared if provided
if [ ! -z "$FILE_TO_COPY" ]; then
    # Check if the file exists
    if [ ! -f "$FILE_TO_COPY" ]; then
        echo "Warning: File to copy '$FILE_TO_COPY' not found, skipping copy operation"
    else
        # Create the shared directory if it doesn't exist
        mkdir -p "$DATA_DIR/$DIR_NAME/shared"
        # Copy the file
        cp "$FILE_TO_COPY" "$DATA_DIR/$DIR_NAME/shared/"
        echo "Copied '$FILE_TO_COPY' to '$DATA_DIR/$DIR_NAME/shared/'"
    fi
fi

echo "Starting $DIR_NAME in tmux session..."
# Create a new tmux session and run the dstack command with verbose output
tmux new-session -d -s $DIR_NAME "dstack run $DATA_DIR/$DIR_NAME  2>&1 | tee /tmp/$DIR_NAME.log"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create tmux session"
    echo "Check /tmp/$DIR_NAME.log for details"
    exit 1
fi

# Wait a moment for the session to start
sleep 2

# Check if the tmux session is running and show its status
if ! tmux has-session -t $DIR_NAME 2>/dev/null; then
    echo "Error: Failed to start $DIR_NAME in tmux session"
    echo "Last few lines of log:"
    tail -n 10 /tmp/$DIR_NAME.log
    exit 1
fi

echo "$DIR_NAME started in tmux session '$DIR_NAME'"
echo "To attach to the session, run: tmux attach -t $DIR_NAME"
echo "To view logs in real-time, run: tail -f /tmp/$DIR_NAME.log"

