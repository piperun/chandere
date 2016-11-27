import re
import urllib.parse

import hypothesis
import hypothesis.strategies as st

from chandere2.validate import (convert_to_regexp, generate_uri,
                                get_filters, get_path, get_targets,
                                split_pattern, strip_target)


class TestGetPath:
    # Asserts that write permissions are properly checked.
    def test_check_output_permissions(self, monkeypatch):
        monkeypatch.setattr("os.access", lambda *args: False)
        assert get_path("/", "ar", "plaintext") is None
        assert get_path("/etc/hosts", "ar", "plaintext") is None

        monkeypatch.setattr("os.access", lambda *args: True)
        assert get_path(".", "ar", "plaintext") is not None
        assert get_path("./README.md", "ar", "plaintext") is not None


    # Asserts that only directories are accepted for file downloading.
    def test_directory_for_file_downloading(self, monkeypatch):
        monkeypatch.setattr("os.access", lambda *args: True)
        assert get_path(".", "fd", "") == "."
        assert get_path("./a_file.txt", "fd", "") is None

    # Asserts that filenames are implicity given for
    # archives if only a directory is given.
    def test_file_for_thread_archiving(self, monkeypatch):
        monkeypatch.setattr("os.access", lambda *args: True)
        assert get_path("./file.txt", "ar", "plaintext") == "./file.txt"
        assert get_path(".", "ar", "sqlite") == "./archive.db"
        assert get_path(".", "ar", "plaintext") == "./archive.txt"


class TestStripTarget:
    # Asserts that a board on its own is properly stripped.
    @hypothesis.given(st.characters(blacklist_characters="/"))
    def test_strip_bare_board(self, target):
        expected_board = urllib.parse.quote(target.strip("/"), safe="/ ",
                                            errors="ignore")

        # None is going to be returned if it's all whitespace.
        if not re.search(r"[^\s\/]", expected_board):
            expected_board = None

        assert strip_target(target) == (expected_board, None)
        assert strip_target("/%s" % target) == (expected_board, None)
        assert strip_target("%s/" % target) == (expected_board, None)
        assert strip_target("/%s/" % target) == (expected_board, None)

    # Asserts that a board and thread are properly stripped.
    @hypothesis.given(st.characters(blacklist_characters="/"),
                      st.integers(min_value=0))
    def test_strip_board_with_thread(self, target_board, target_thread):
        expected_thread = str(target_thread)
        expected_board = urllib.parse.quote(target_board.strip("/"),
                                            safe="/ ", errors="ignore")

        # If the given target lacks a valid board initial but a thread
        # is given, the thread will be interpreted as a board.
        if not re.search(r"[^\s\/]", expected_board):
            expected_board = str(target_thread)
            expected_thread = None

        target = "/".join((target_board, str(target_thread)))
        assert strip_target(target) == (expected_board, expected_thread)


class TestGenerateUri:
    # Asserts that the board initial and the
    # threads endpoint are in the URI.
    @hypothesis.given(st.text())
    def test_create_url_with_board(self, board):
        uri = generate_uri(board, None, "4chan")
        assert board in uri
        assert "threads.json" in uri

        uri = generate_uri(board, None, "uboachan")
        assert board in uri
        assert "threads.json" in uri

        uri = generate_uri(board, None, "endchan")
        assert board in uri
        assert "catalog.json" in uri

    # Asserts that the board and thread are in the
    # URI, and that the threads endpoint is not.
    @hypothesis.given(st.text(), st.integers(min_value=0))
    def test_create_url_with_thread(self, board, thread):
        uri = generate_uri(board, str(thread), "4chan")
        assert "/".join((board, "thread", str(thread))) in uri
        assert "threads.json" not in uri

        uri = generate_uri(board, str(thread), "8chan")
        assert "/".join((board, "res", str(thread))) in uri
        assert "threads.json" not in uri

        uri = generate_uri(board, str(thread), "endchan")
        assert "/".join((board, "res", str(thread))) in uri
        assert "catalog.json" not in uri

    # Asserts that None is returned when the
    # imageboard is not a known alias.
    def test_fail_on_unknown_imageboard(self):
        assert generate_uri("b", "", "7chan") is None
        assert generate_uri("c", "", "krautchan") is None
        assert generate_uri("silicon", "", "sushigirl") is None


class TestGetTargets:
    # Asserts that a board initial is properly handled.
    @hypothesis.given(st.characters(blacklist_characters="/ "))
    def test_get_single_board(self, board):
        escaped = urllib.parse.quote(board, safe="/ ", errors="ignore").strip()

        # Hardcoded test for 4chan.
        if not escaped and not re.search(r"[^\s\/]", escaped):
            expected_result = {}
            expected_failed = [board]
        else:
            expected_uri = "http://a.4cdn.org/%s/threads.json" % escaped
            expected_result = {expected_uri: [escaped, False, ""]}
            expected_failed = []
        parsed, failed = get_targets([board], "4chan", False)
        assert parsed == expected_result
        assert failed == expected_failed

        # Hardcoded test for 8chan.
        if expected_result:
            expected_uri = "http://8ch.net/%s/threads.json" % escaped
            expected_result = {expected_uri: [escaped, False, ""]}
        parsed, failed = get_targets([board], "8chan", False)
        assert parsed == expected_result
        assert failed == expected_failed

        # Hardcoded test for Lainchan.
        if expected_result:
            expected_uri = "http://lainchan.org/%s/threads.json" % escaped
            expected_result = {expected_uri: [escaped, False, ""]}
        parsed, failed = get_targets([board], "lainchan", False)
        assert parsed == expected_result
        assert failed == expected_failed

    # Asserts that a board and thread are proprely handled.
    @hypothesis.given(st.characters(blacklist_characters="/"),
                      st.integers(min_value=0))
    def test_get_board_and_thread(self, board, thread):
        # Hardcoded tests for 4chan.
        target = "/".join((board, str(thread)))
        escaped = urllib.parse.quote(board, safe="/ ", errors="ignore").strip()
        if not re.search(r"[^\s\/]", escaped):
            expected_uri = "http://a.4cdn.org/%d/threads.json" % thread
            expected_result = {expected_uri: [str(thread), False, ""]}
        else:
            expected_uri = "http://a.4cdn.org/%s/thread/%s.json" % (escaped,
                                                                    thread)
            expected_result = {expected_uri: [escaped, True, ""]}
        parsed, failed = get_targets([target], "4chan", False)
        assert parsed == expected_result
        assert not failed

        # Hardcoded tests for 8chan.
        target = "/".join((board, str(thread)))
        escaped = urllib.parse.quote(board, safe="/ ", errors="ignore").strip()
        if not re.search(r"[^\s\/]", escaped):
            expected_uri = "http://8ch.net/%d/threads.json" % thread
            expected_result = {expected_uri: [str(thread), False, ""]}
        else:
            expected_uri = "http://8ch.net/%s/res/%s.json" % (escaped, thread)
            expected_result = {expected_uri: [escaped, True, ""]}
        parsed, failed = get_targets([target], "8chan", False)
        assert parsed == expected_result
        assert not failed

        # Hardcoded tests for Lainchan.
        target = "/".join((board, str(thread)))
        escaped = urllib.parse.quote(board, safe="/ ", errors="ignore").strip()
        if not re.search(r"[^\s\/]", escaped):
            expected_uri = "http://lainchan.org/%d/threads.json" % thread
            expected_result = {expected_uri: [str(thread), False, ""]}
        else:
            expected_uri = "http://lainchan.org/%s/res/%s.json" % (escaped,
                                                                   thread)
            expected_result = {expected_uri: [escaped, True, ""]}
        parsed, failed = get_targets([target], "lainchan", False)
        assert parsed == expected_result
        assert not failed

    # Asserts failure when a board is omitted.
    def test_fail_invalid_target(self):
        # Hardcoded test for 4chan.
        parsed, failed = get_targets(["/"], "4chan", False)
        assert not parsed
        assert "/" in failed

        # Hardcoded test for 8chan.
        parsed, failed = get_targets(["/"], "8chan", False)
        assert not parsed
        assert "/" in failed

        # Hardcoded test for Lainchan.
        parsed, failed = get_targets(["/"], "lainchan", False)
        assert not parsed
        assert "/" in failed

    # Asserts failure when a valid URI cannot be created.
    def test_fail_invalid_uri(self):
        parsed, failed = get_targets(["b"], "7chan", False)
        assert not parsed
        assert "b" in failed

        parsed, failed = get_targets(["c"], "krautchan", False)
        assert not parsed
        assert "c" in failed

        parsed, failed = get_targets(["silicon"], "sushigirl", False)
        assert not parsed
        assert "silicon" in failed


class TestConvertToRegexp:
    # Asserts that explicitly listed regular expressions are untouched.
    @hypothesis.given(st.characters(blacklist_characters="\n.?*+()[]\\/"))
    def test_ignore_expicit_regex(self, pattern):
        parsed = convert_to_regexp("/%s/" % pattern)
        assert parsed == pattern

        parsed = convert_to_regexp("%s/%s/" % (pattern, pattern))
        assert parsed == "%s%s" % (pattern, pattern)

        parsed = convert_to_regexp("/%s/%s" % (pattern, pattern))
        assert parsed == "%s%s" % (pattern, pattern)

    # Asserts that regex special characters are escaped.
    @hypothesis.given(st.characters(blacklist_characters="\n*"))
    def test_escape_patterns(self, pattern):
        expected = pattern
        for character in ".?+()[]/\\":
            expected = expected.replace(character, "\\" + character)

        assert convert_to_regexp(pattern) == expected

    # Asserts that wildcards are properly replaced
    @hypothesis.given(st.characters(blacklist_characters="\n.?+()[]\\/"))
    def test_replace_wildcards(self, pattern):
        expected = re.sub(r"\*(\s|$)", ".*", pattern)
        expected = re.sub(r"\*(?=\w)", ".", expected)

        assert convert_to_regexp(pattern) == expected


class TestSplitPattern:
    # Asserts that whitespace is properly handled.
    @hypothesis.given(
        st.lists(
            elements=st.characters(blacklist_characters="\"")
        )
    )
    def test_use_and_operator(self, pattern):
        expected = list(filter(lambda x: x.strip(), pattern))
        assert list(split_pattern(" ".join(pattern))) == expected

    # Asserts that exact matches are untouched.
    @hypothesis.given(
        st.lists(
            elements=st.characters(blacklist_characters="\"\n")
        ),
        st.lists(
            elements=st.characters(blacklist_characters="\"\n")
        ),
        st.lists(
            elements=st.characters(blacklist_characters="\"\n")
        )
    )
    def test_use_exact_match(self, prefix, exact, postfix):
        pattern = " \" ".join(map(" ".join, (prefix, exact, postfix)))
        expected = prefix if prefix else []
        if exact and "".join(exact).strip():
            expected.append(" ".join(exact).strip())
        if postfix:
            expected += postfix
        expected = filter(lambda x: not re.search(r"^\s*$", x), expected)
        assert sorted(list(split_pattern(pattern))) == sorted(expected)


class TestGetFilters:
    # Asserts that filters are properly processed.
    @hypothesis.given(st.characters(blacklist_characters=":"),
                      st.characters(blacklist_characters=":"))
    def test_evaluate_filters(self, field, pattern):
        if not re.search(r"[^\s]", pattern.strip()):
            return

        # Imageboard is unimportant to the subroutine at this point.
        evaluated, failed = get_filters([":".join((field, pattern))], "4chan")
        evaluated_field, evaluated_pattern = evaluated[0]
        assert evaluated_field == field
        assert evaluated_pattern == convert_to_regexp(pattern)
        assert not failed

    # Asserts that failed patterns are properly returned.
    @hypothesis.given(st.characters(blacklist_characters=":"))
    def test_evaluate_failed(self, pattern):
        evaluated, failed = get_filters([pattern], "4chan")
        assert not evaluated
        assert failed == [pattern]
