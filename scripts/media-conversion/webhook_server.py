#!/usr/bin/env python3
"""
Webhook server to receive Jellyfin playback events
and trigger smart download logic
"""

from flask import Flask, request, jsonify
import subprocess
import json
import logging
import os

app = Flask(__name__)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/conversions/webhook_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SMART_DOWNLOAD_SCRIPT = '/app/smart_download.py'


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/jellyfin/playback', methods=['POST'])
def jellyfin_playback():
    """Handle Jellyfin playback events"""
    try:
        event_data = request.json
        logger.info(f"Received playback event: {event_data.get('Item', {}).get('Name', 'Unknown')}")

        # Only process playback stop events (full watch)
        event_type = event_data.get('Event', '')
        if event_type not in ['PlaybackStop', 'item.markplayed']:
            logger.info(f"Ignoring event type: {event_type}")
            return jsonify({'status': 'ignored', 'reason': 'not a complete playback'}), 200

        # Check if watch was completed (>90% watched)
        playback_info = event_data.get('PlaybackInfo', {})
        position_ticks = playback_info.get('PositionTicks', 0)
        runtime_ticks = event_data.get('Item', {}).get('RunTimeTicks', 1)

        if runtime_ticks > 0:
            watch_percentage = (position_ticks / runtime_ticks) * 100
            if watch_percentage < 90:
                logger.info(f"Incomplete watch ({watch_percentage:.1f}%), skipping")
                return jsonify({'status': 'ignored', 'reason': 'incomplete watch'}), 200

        # Call smart download script
        result = subprocess.run(
            ['/usr/bin/python3', SMART_DOWNLOAD_SCRIPT],
            input=json.dumps(event_data),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            logger.info(f"Smart download script executed successfully")
            return jsonify({'status': 'success', 'output': result.stdout}), 200
        else:
            logger.error(f"Smart download script failed: {result.stderr}")
            return jsonify({'status': 'error', 'error': result.stderr}), 500

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/jellyfin/generic', methods=['POST'])
def jellyfin_generic():
    """Handle generic Jellyfin webhook events"""
    try:
        data = request.json
        logger.info(f"Received generic Jellyfin event: {json.dumps(data)[:200]}")
        return jsonify({'status': 'received'}), 200
    except Exception as e:
        logger.error(f"Error processing generic webhook: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


if __name__ == '__main__':
    # Run on port 5000, accessible from Docker network
    app.run(host='0.0.0.0', port=5000, debug=False)
