#!/bin/bash
# Scan existing movie library and populate analytics database

echo "=========================================================================="
echo "                    MOVIE LIBRARY SCANNER"
echo "=========================================================================="
echo ""

MOVIES_DIR="/data/media/movies"
TOTAL=0
SUCCESS=0
FAILED=0

echo "Scanning: $MOVIES_DIR"
echo ""

# Find all MKV files
while IFS= read -r -d '' file; do
    ((TOTAL++))

    echo "[$TOTAL] Processing: $(basename "$file")"
    echo "    Path: $file"

    # Run corruption tracker to log metadata (doesn't convert, just logs)
    if docker exec media-converter python3 /app/corruption_tracker.py "$file" > /dev/null 2>&1; then
        ((SUCCESS++))
        echo "    ✓ Metadata logged successfully"
    else
        ((FAILED++))
        echo "    ✗ Failed to extract metadata"
    fi

    echo ""

done < <(find "$MOVIES_DIR" -type f -name "*.mkv" -print0)

echo "=========================================================================="
echo "                         SCAN COMPLETE"
echo "=========================================================================="
echo "Total files scanned:  $TOTAL"
echo "Successfully logged:  $SUCCESS"
echo "Failed to process:    $FAILED"
echo ""
echo "View analytics with:"
echo "  ./analyze.sh summary"
echo "  ./analyze.sh recommended"
echo "  ./analyze.sh hdr-reliable"
echo "=========================================================================="
