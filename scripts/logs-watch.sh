#!/bin/bash

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
    echo "Usage: $0 [service_name] [options]"
    echo
    echo "Options:"
    echo "  -f, --follow     Follow log output (default)"
    echo "  -n, --tail NUM   Number of lines to show (default: 100)"
    echo "  -e, --errors     Show only errors"
    echo "  -s, --since TIME Show logs since timestamp"
    echo
    echo "Examples:"
    echo "  $0 api"
    echo "  $0 worker --tail 500"
    echo "  $0 --errors"
    echo "  $0 api --since 2024-10-13T12:00:00"
    exit 1
}

SERVICE=""
FOLLOW="-f"
TAIL="100"
GREP_PATTERN=""
SINCE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -n|--tail)
            TAIL="$2"
            shift 2
            ;;
        -e|--errors)
            GREP_PATTERN="error|exception|failed|fatal"
            shift
            ;;
        -s|--since)
            SINCE="--since $2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        --no-follow)
            FOLLOW=""
            shift
            ;;
        *)
            if [ -z "$SERVICE" ]; then
                SERVICE="$1"
            fi
            shift
            ;;
    esac
done

echo -e "${BLUE}=== Trading Bot Logs ===${NC}"
if [ -n "$SERVICE" ]; then
    echo -e "${GREEN}Service: $SERVICE${NC}"
else
    echo -e "${GREEN}All services${NC}"
fi
echo

# Build command
CMD="$DOCKER_COMPOSE -p $PROJECT_NAME logs $FOLLOW --tail=$TAIL $SINCE"

if [ -n "$SERVICE" ]; then
    CMD="$CMD $SERVICE"
fi

# Execute
if [ -n "$GREP_PATTERN" ]; then
    eval "$CMD" | grep -iE "$GREP_PATTERN" --color=always
else
    eval "$CMD"
fi