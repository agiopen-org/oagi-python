# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import pytest

from oagi.utils.prompt_builder import build_prompt


class TestBuildPrompt:
    def test_qwen3_default_prompt(self):
        prompt = build_prompt("Open browser")

        assert "Please generate the next move" in prompt
        assert "Instruction: Open browser" in prompt
        assert "Previous actions:\nNone" in prompt

    def test_qwen3_prompt_with_previous_actions(self):
        prompt = build_prompt(
            "Open browser",
            previous_actions="Step 1: Click Firefox icon.",
            prompt_mode="qwen3",
        )

        assert "Step 1: Click Firefox icon." in prompt

    def test_legacy_prompt(self):
        prompt = build_prompt("Open browser", prompt_mode="legacy")

        assert "<|think_start|>" in prompt
        assert "<|action_start|>" in prompt

    def test_invalid_prompt_mode_raises(self):
        with pytest.raises(ValueError, match="Unsupported prompt_mode"):
            build_prompt("Open browser", prompt_mode="invalid")  # type: ignore[arg-type]
