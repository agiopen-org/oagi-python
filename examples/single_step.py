# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import single_step

step = single_step(
    task_description="Search weather with Google",
    screenshot="some/path/to/local/image",  # bytes or Path object or Image object
    instruction="The operating system is macos",  # optional instruction
    # api_key="your-api-key", if not set with OAGI_API_KEY env var
    # base_url="https://api.example.com" if not set with OAGI_BASE_URL env var
)

print(step)
