if [ -z "$1" ]; then
    echo "Error: DATA_DIR parameter is required"
    echo "Usage: $0 <data_dir>"
    exit 1
fi
DATA_DIR="$1"
DIR_NAME="guest_manager"
PRIVATE_ML_SDK_DIR="/home/ubuntu/private-ml-sdk"

rm -rf $DATA_DIR/$DIR_NAME

echo "Creating dstack instance..."
# Run dstack new and check for failure
dstack new guest_manager.yaml -o $DATA_DIR/$DIR_NAME --image $PRIVATE_ML_SDK_DIR/images/dstack-dev-0.3.5/ -c 12 -m 32G -d 2T --port tcp:10022:22 --port tcp:0.0.0.0:10080:80 --port tcp:0.0.0.0:32768:32768-32868
if [ $? -ne 0 ]; then
    echo "Error: Failed to create dstack instance"
    exit 1
fi

echo "Starting guest manager in tmux session..."
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
    echo "Error: Failed to start guest manager in tmux session"
    echo "Last few lines of log:"
    tail -n 10 /tmp/$DIR_NAME.log
    exit 1
fi

echo "Guest manager started in tmux session '$DIR_NAME'"
echo "To attach to the session, run: tmux attach -t $DIR_NAME"
echo "To view logs in real-time, run: tail -f /tmp/$DIR_NAME.log"

