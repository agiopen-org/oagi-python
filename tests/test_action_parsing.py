# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import pytest

from oagi.types import parse_coords, parse_drag_coords, parse_scroll


class TestParseCoords:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("500, 300", (500, 300)),
            ("500,300,", (500, 300)),
            ("0, 0", (0, 0)),
            ("1000, 1000", (1000, 1000)),
            ("123,456", (123, 456)),
            ("  500 ,  300  ", None),  # spaces before digits not supported
        ],
    )
    def test_valid_coords(self, input_str, expected):
        assert parse_coords(input_str) == expected

    @pytest.mark.parametrize(
        "input_str",
        [
            "",
            "invalid",
            "500",
            "500,",
            ",300",
            "abc, def",
            "500.5, 300.5",
        ],
    )
    def test_invalid_coords(self, input_str):
        assert parse_coords(input_str) is None


class TestParseDragCoords:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("100, 100, 500, 500", (100, 100, 500, 500)),
            ("100,100,500,500,", (100, 100, 500, 500)),
            ("0, 0, 1000, 1000", (0, 0, 1000, 1000)),
            ("50,50,200,300", (50, 50, 200, 300)),
        ],
    )
    def test_valid_drag_coords(self, input_str, expected):
        assert parse_drag_coords(input_str) == expected

    @pytest.mark.parametrize(
        "input_str",
        [
            "",
            "invalid",
            "100, 100, 500",
            "100, 100",
            "100",
            "abc, def, ghi, jkl",
        ],
    )
    def test_invalid_drag_coords(self, input_str):
        assert parse_drag_coords(input_str) is None


class TestParseScroll:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("500, 300, up", (500, 300, "up")),
            ("500,300,down,", (500, 300, "down")),
            ("500, 300, UP", (500, 300, "up")),
            ("500, 300, Down", (500, 300, "down")),
            ("0, 0, up", (0, 0, "up")),
        ],
    )
    def test_valid_scroll(self, input_str, expected):
        assert parse_scroll(input_str) == expected

    @pytest.mark.parametrize(
        "input_str",
        [
            "",
            "invalid",
            "500, 300",
            "500",
            "500, 300,",
            "500, 300, left",  # invalid direction
            "500, 300, right",  # invalid direction
            "500, 300, invalid_direction",  # invalid direction
        ],
    )
    def test_invalid_scroll(self, input_str):
        assert parse_scroll(input_str) is None
