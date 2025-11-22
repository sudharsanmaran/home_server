#!/bin/bash
# Quick analytics wrapper for common queries

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYTICS="$SCRIPT_DIR/corruption_analytics.py"

case "$1" in
    "")
        echo "Media Corruption Analytics"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Overview Commands:"
        echo "  summary              Show overall summary"
        echo "  success              Show successful conversions stats"
        echo "  all                  Run all reports"
        echo ""
        echo "Publisher Analysis:"
        echo "  recommended          Show recommended publishers (for Radarr)"
        echo "  worst                Show worst publishers"
        echo "  best                 Show best publishers"
        echo "  quality              Show quality scores for all publishers"
        echo "  hdr-reliable         Most reliable HDR/DV publishers"
        echo "  search <name>        Search for specific publisher"
        echo ""
        echo "Format & Source Analysis:"
        echo "  hdr                  HDR/Dolby Vision analysis"
        echo "  formats              Analyze by format"
        echo "  sources              Analyze by source type"
        echo ""
        echo "Recent Activity:"
        echo "  recent               Show recent corruptions"
        echo ""
        echo "Export:"
        echo "  export-radarr <file> Export Radarr config with preferred publishers"
        echo ""
        ;;
    summary)
        python3 "$ANALYTICS" summary
        ;;
    success)
        python3 "$ANALYTICS" success-summary
        ;;
    recommended)
        python3 "$ANALYTICS" recommended
        ;;
    worst)
        python3 "$ANALYTICS" worst-publishers "$@"
        ;;
    best)
        python3 "$ANALYTICS" best-publishers "$@"
        ;;
    quality)
        python3 "$ANALYTICS" quality-scores "$@"
        ;;
    hdr-reliable)
        python3 "$ANALYTICS" hdr-reliable
        ;;
    recent)
        python3 "$ANALYTICS" recent "$@"
        ;;
    hdr)
        python3 "$ANALYTICS" hdr
        ;;
    formats)
        python3 "$ANALYTICS" formats
        ;;
    sources)
        python3 "$ANALYTICS" sources
        ;;
    all)
        python3 "$ANALYTICS" all
        ;;
    search)
        if [ -z "$2" ]; then
            echo "Error: Please provide a publisher name"
            echo "Usage: $0 search <publisher_name>"
            exit 1
        fi
        python3 "$ANALYTICS" search "$2"
        ;;
    export-radarr)
        if [ -z "$2" ]; then
            echo "Error: Please provide an output filename"
            echo "Usage: $0 export-radarr <output_file>"
            exit 1
        fi
        python3 "$ANALYTICS" export-radarr "$2"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run '$0' without arguments to see available commands"
        exit 1
        ;;
esac
