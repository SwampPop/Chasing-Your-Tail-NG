#!/usr/bin/env python3
"""CYT API Server with CORS enabled for dashboard access."""
import sys
import os

# Ensure we're in the right directory
os.chdir('/media/psf/my_projects/0_active_projects/Chasing-Your-Tail-NG')
sys.path.insert(0, '/media/psf/my_projects/0_active_projects/Chasing-Your-Tail-NG')

# Set API key from environment or default
if 'CYT_API_KEY' not in os.environ:
    os.environ['CYT_API_KEY'] = '4irSMYe38Y-5ONUPhcsPr5MtFx2ViKrkTvhea3YuN9Y'

from flask_cors import CORS
from api_server import app

# Enable CORS for all routes
CORS(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
