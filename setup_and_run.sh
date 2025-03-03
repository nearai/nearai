#!/bin/bash
# setup_and_run.sh
# This script handles setting up the environment and running the Near AI Hub
# It includes setup, database migrations, and running the application
# Log function for better visibility
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}
# Error handling
set -e
trap 'log "Error occurred at line $LINENO. Command: $BASH_COMMAND"' ERR
# Step 1: Make sure we're in the correct directory
check_directory() {
    local path=$1

    log "Changing to directory '$path'..."
    cd "$path" || { log "Directory '$path' not found"; exit 1; }
    log "Successfully changed to directory: $(pwd)"
}
# Step 2: Setup virtual environment
setup_venv() {
    log "Setting up virtual environment..."
    if [[ ! -d "venv" ]]; then
        python -m venv venv
        log "Virtual environment created"
    else
        log "Virtual environment already exists"
    fi
    log "Activating virtual environment..."
    source venv/bin/activate
}
# Step 3: Install dependencies
install_deps() {
    log "Installing dependencies..."
    pip install -e .
    pip install -e .[hub]
    log "Dependencies installed successfully"
}
# Step 4: Run database migrations
run_migrations() {
    log "Running database migrations..."
    cd hub
    alembic upgrade head
    cd ..
    log "Database migrations completed"
}
# Step 5: Kill any existing process
kill_processes() {
    stop_all
}
# Step 6: Run the API server
run_api() {
    local workers=$1
    local port=$2
    local process_name="nearai-hub-worker"  # Process name to identify workers

    log "Starting FastAPI server with $workers workers on port $port..."

    # Backup old log file with timestamp
    [ -f ./api.log ] && mv ./api.log "./api_$(date +%Y-%m-%d_%H-%M-%S).log"

    # Start the API server with specified number of workers
    nohup env PYTHON_PROCESS_NAME="${process_name}" uvicorn app:app --workers $workers --host 0.0.0.0 --port $port > ./api.log 2>&1 &

    # Capture the PID of the main process (the parent process)
    local api_pid=$!
    echo $api_pid > api.pid
    log "FastAPI server started with PID $api_pid and $workers workers."

    log "API server started with $workers workers on port $port."
}
# Step 7: Run the scheduler
run_scheduler() {
    log "Starting scheduler as a separate process..."

     # Backup old log file with timestamp
    [ -f ./scheduler.log ] && mv ./scheduler.log "./scheduler_$(date +%Y-%m-%d_%H-%M-%S).log"

    nohup python scheduler.py > ./scheduler.log 2>&1 &

    local scheduler_pid=$!
    echo $scheduler_pid > scheduler.pid
    log "Scheduler started with PID $scheduler_pid"
}
# Main function to run everything
main() {
    local workers=${1:-8}
    local port=${2:-8001}
    local path=${3:-"/nearai"}

    check_directory "$path"
    setup_venv
    install_deps
    run_migrations

    cd hub

    # Kill any existing processes
    kill_processes

    # Start the API and scheduler
    run_api "$workers" "$port"
    run_scheduler

    log "Setup and deployment completed successfully!"
    log "API running on port $port with $workers workers"
    log "Check ./api.log and ./scheduler.log for details"
}
restart() {
    local workers=${1:-8}
    local port=${2:-8001}
    local path=${3:-"/nearai"}

    log "Restarting processes without installation..."

    # Check directory
    check_directory "$path"

    # Activate virtual environment if exists
    if [[ -d "venv" ]]; then
        log "Activating virtual environment..."
        source venv/bin/activate
    else
        log "Error: Virtual environment 'venv' not found. Please run setup first."
        exit 1
    fi

    cd hub

    # Stop all processes
    stop_all

    # Start API and scheduler
    run_api "$workers" "$port"
    run_scheduler

    log "Restart completed successfully!"
    log "API running on port $port with $workers workers"
    log "Check ./api.log and ./scheduler.log for details"
}
# Help message
show_help() {
    echo "Usage: ./setup_and_run.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  [workers] [port] [path]  Start the application with specified parameters (default)"
    echo "  stop                     Stop all running processes"
    echo "  restart [workers] [port] [path]  Restart processes without reinstallation"
    echo "  --help, -h               Show this help message"
    echo ""
    echo "Options:"
    echo "  workers     Number of worker processes (default: 8)"
    echo "  port        Port to run the API on (default: 8001)"
    echo "  path        Directory path (default: /nearai)"
    echo ""
    echo "Examples:"
    echo "  ./setup_and_run.sh                        # Start with default settings"
    echo "  ./setup_and_run.sh 4 8000                 # Start with 4 workers on port 8000"
    echo "  ./setup_and_run.sh restart 4 8000         # Restart with custom workers and port"
    echo "  ./setup_and_run.sh stop                   # Stop all processes"

}
# Stop all processes
stop_all() {
    log "Stopping API and scheduler processes..."

    # Stopping API process
    if [ -f api.pid ]; then
        local api_pid=$(cat api.pid)
        if kill -0 "$api_pid" 2>/dev/null; then
            kill "$api_pid" 2>/dev/null
            log "Sent termination signal to API process (PID: $api_pid)"
            sleep 1  # Wait for process to terminate
            if kill -0 "$api_pid" 2>/dev/null; then
                kill -9 "$api_pid" 2>/dev/null
                log "Forced termination of API process (PID: $api_pid)"
            fi
        else
            log "API process (PID: $api_pid) not running"
        fi
        rm api.pid
    fi

    # If the API process is still running (PID didn't work or file wasn't there), kill by name
    pkill -f "nearai-hub-worker" || true
    pkill -f "multiprocessing.spawn" || true
    log "API process killed by pkill"

    # Stopping scheduler process
    if [ -f scheduler.pid ]; then
        local scheduler_pid=$(cat scheduler.pid)
        if kill -0 "$scheduler_pid" 2>/dev/null; then
            kill "$scheduler_pid" 2>/dev/null
            log "Sent termination signal to scheduler process (PID: $scheduler_pid)"
            sleep 1  # Wait for process to terminate
            if kill -0 "$scheduler_pid" 2>/dev/null; then
                kill -9 "$scheduler_pid" 2>/dev/null
                log "Forced termination of scheduler process (PID: $scheduler_pid)"
            fi
        else
            log "Scheduler process (PID: $scheduler_pid) not running"
        fi
        rm scheduler.pid
    fi

    # If the scheduler process is still running (PID didn't work or file wasn't there), kill by name
    pkill -f "python scheduler.py" || true
    log "Scheduler process killed by pkill"

    log "All processes stopped."
}


stop_processes() {
  local path=${1:-"/nearai"}

  check_directory "$path"

  cd hub

  stop_all
}

# Command processing
case "$1" in
    --help|-h)
        show_help
        exit 0
        ;;
    stop)
        shift
        stop_processes "$@"
        exit 0
        ;;
    restart)
        shift
        restart "$@"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac