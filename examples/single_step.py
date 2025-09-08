# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from oagi import ScreenshotMaker, single_step

image_provider = ScreenshotMaker()
image = image_provider()
step = single_step(
    task_description="Search weather with Google",
    screenshot=image,  # bytes or Path object or Image object
    instruction="The operating system is macos",  # optional instruction
    api_key="sk-50DPDW87GnlNcH_0cAPRFZ4ntweCEdUrLEFIcQFaBhc",
    base_url="http://127.0.0.1:8000",
)

print(step)
