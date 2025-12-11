# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

# URLs & API Endpoints
DEFAULT_BASE_URL = "https://api.agiopen.org"
API_KEY_HELP_URL = "https://developer.agiopen.org/api-keys"
API_V1_FILE_UPLOAD_ENDPOINT = "/v1/file/upload"
API_V1_GENERATE_ENDPOINT = "/v1/generate"

# Model identifiers
MODEL_ACTOR = "lux-actor-1"
MODEL_THINKER = "lux-thinker-1"

# Agent modes
MODE_ACTOR = "actor"
MODE_THINKER = "thinker"
MODE_TASKER = "tasker"

# Default max steps per model
DEFAULT_MAX_STEPS = 20
DEFAULT_MAX_STEPS_THINKER = 100
DEFAULT_MAX_STEPS_TASKER = 60

# Maximum allowed steps per model (hard limits)
MAX_STEPS_ACTOR = 30
MAX_STEPS_THINKER = 120

# Reflection intervals
DEFAULT_REFLECTION_INTERVAL = 4
DEFAULT_REFLECTION_INTERVAL_TASKER = 20

# Timing & Delays
DEFAULT_STEP_DELAY = 0.3

# Temperature Defaults
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TEMPERATURE_LOW = 0.1

# Timeout Values
HTTP_CLIENT_TIMEOUT = 60
