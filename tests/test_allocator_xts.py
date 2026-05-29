"""Validate allocator.xts structure: all cross-references resolve, all guide/manual
sections are defined, and command groups match actual definitions.

These tests parse the .xts file directly — no server needed.
"""

import re
import os
import pytest
import yaml

XTS_PATH = os.path.join(os.path.dirname(__file__), "..", "allocator.xts")


@pytest.fixture(scope="module")
def xts_raw():
    """Raw text of allocator.xts."""
    with open(XTS_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def xts_data(xts_raw):
    """Parsed YAML from allocator.xts."""
    return yaml.safe_load(xts_raw)


@pytest.fixture(scope="module")
def defined_commands(xts_data):
    """Set of top-level command names (keys that have a 'command' or 'description' sub-key)."""
    skip_keys = {"brief", "alias_name", "command_groups", "functions"}
    commands = set()
    for key, value in xts_data.items():
        if key in skip_keys:
            continue
        if isinstance(value, dict):
            commands.add(key)
    return commands


# ── Guide commands ───────────────────────────────────────────────────

class TestGuideCommands:
    """Verify all guide_* commands are defined and registered."""

    EXPECTED_GUIDES = [
        "guide",
        "guide_quickstart",
        "guide_server",
        "guide_allocation",
        "guide_search",
        "guide_testing",
        "guide_borrowing",
        "guide_state",
        "guide_authentication",
    ]

    @pytest.mark.parametrize("cmd", EXPECTED_GUIDES)
    def test_guide_command_defined(self, defined_commands, cmd):
        """Each guide command must exist as a top-level key."""
        assert cmd in defined_commands, f"'{cmd}' not defined in allocator.xts"

    @pytest.mark.parametrize("cmd", EXPECTED_GUIDES)
    def test_guide_command_has_description(self, xts_data, cmd):
        """Each guide command must have a description."""
        assert "description" in xts_data[cmd], f"'{cmd}' missing description"

    @pytest.mark.parametrize("cmd", EXPECTED_GUIDES)
    def test_guide_command_has_command_block(self, xts_data, cmd):
        """Each guide command must have a command block."""
        assert "command" in xts_data[cmd], f"'{cmd}' missing command block"

    @pytest.mark.parametrize("cmd", EXPECTED_GUIDES)
    def test_guide_in_command_groups(self, xts_data, cmd):
        """Each guide command must be listed in command_groups."""
        all_grouped = []
        for group in xts_data.get("command_groups", {}).values():
            all_grouped.extend(group.get("commands", []))
        assert cmd in all_grouped, f"'{cmd}' not listed in any command_group"


# ── Manual sections ──────────────────────────────────────────────────

class TestManualSections:
    """Verify all manual sections are handled."""

    EXPECTED_SECTIONS = [
        "overview",
        "commands",
        "api",
        "states",
        "workflows",
        "troubleshooting",
    ]

    def test_manual_command_defined(self, defined_commands):
        assert "manual" in defined_commands

    @pytest.mark.parametrize("section", EXPECTED_SECTIONS)
    def test_manual_section_handled(self, xts_data, section):
        """Each section must appear in the manual case statement."""
        manual_cmd = xts_data["manual"]["command"]
        assert section in manual_cmd, (
            f"Manual section '{section}' not handled in case statement"
        )

    @pytest.mark.parametrize("section", EXPECTED_SECTIONS)
    def test_manual_section_not_todo(self, xts_data, section):
        """No manual section should still be a TODO stub."""
        manual_cmd = xts_data["manual"]["command"]
        # Find the case block for this section
        # Pattern: section appears in a case line, then check the block doesn't contain TODO
        pattern = rf'{section}\b.*\).*?;;'
        match = re.search(pattern, manual_cmd, re.DOTALL)
        if match:
            block = match.group(0)
            assert "TODO:" not in block, (
                f"Manual section '{section}' still contains a TODO stub"
            )

    def test_manual_sections_listed_in_description(self, xts_data):
        """The manual description should list all sections."""
        desc = xts_data["manual"]["description"]
        for section in self.EXPECTED_SECTIONS:
            assert section in desc, (
                f"Section '{section}' not listed in manual description"
            )


# ── Cross-references ─────────────────────────────────────────────────

class TestCrossReferences:
    """Verify every 'xts allocator <command>' reference in echo text
    points to a command that actually exists."""

    def test_all_echo_references_resolve(self, xts_raw, defined_commands):
        """Every 'xts allocator <cmd>' in echo output must reference a real command."""
        # Match: xts allocator <word> where word looks like a command name
        # Exclude patterns like 'xts allocator guide_<topic>' (template) and
        # things inside comments or description blocks
        pattern = re.compile(r'xts allocator (\w+)')
        unresolved = set()

        for match in pattern.finditer(xts_raw):
            cmd = match.group(1)
            # Skip template patterns, flags, and non-command references
            if cmd.startswith("<") or cmd.startswith("--") or cmd == "manual":
                continue
            # Skip partial matches from template syntax like 'guide_<topic>'
            if cmd.endswith("_"):
                continue
            # 'manual' is followed by a section argument, not a command
            # Check if the match is 'xts allocator manual <section>'
            # In that case 'manual' is the command, which is valid
            if cmd not in defined_commands:
                # Get line for context
                start = xts_raw.rfind("\n", 0, match.start()) + 1
                end = xts_raw.find("\n", match.end())
                line = xts_raw[start:end].strip()
                # Only flag if it's in an echo/command block (not a comment)
                if not line.startswith("#"):
                    unresolved.add(cmd)

        # These are known non-command references (arguments to manual, etc.)
        known_non_commands = {
            "workflows", "overview", "api", "commands", "states",
            "troubleshooting", "health",
        }
        actual_unresolved = unresolved - known_non_commands - defined_commands

        assert not actual_unresolved, (
            f"Unresolved command references in allocator.xts: {sorted(actual_unresolved)}"
        )

    def test_no_space_separated_guide_references(self, xts_raw):
        """Ensure no 'xts allocator guide <subject>' with a space — must use underscore."""
        # This catches the bug we fixed: 'guide allocation' instead of 'guide_allocation'
        guide_subjects = [
            "quickstart", "server", "allocation", "search",
            "testing", "borrowing", "state", "authentication",
        ]
        for subject in guide_subjects:
            # Match 'allocator guide <subject>' but NOT 'allocator guide_<subject>'
            pattern = rf'allocator guide {subject}'
            matches = re.findall(pattern, xts_raw)
            assert not matches, (
                f"Found space-separated guide reference 'guide {subject}' "
                f"— should be 'guide_{subject}'"
            )


# ── Command groups completeness ──────────────────────────────────────

class TestCommandGroups:
    """Verify command_groups are consistent with definitions."""

    def test_all_grouped_commands_exist(self, xts_data, defined_commands):
        """Every command listed in a group must be defined."""
        missing = []
        for group_name, group in xts_data.get("command_groups", {}).items():
            for cmd in group.get("commands", []):
                if cmd not in defined_commands:
                    missing.append(f"{group_name}/{cmd}")

        assert not missing, f"Commands in groups but not defined: {missing}"

    def test_all_defined_commands_are_grouped(self, xts_data, defined_commands):
        """Every defined command should appear in at least one group."""
        all_grouped = set()
        for group in xts_data.get("command_groups", {}).values():
            all_grouped.update(group.get("commands", []))

        ungrouped = defined_commands - all_grouped
        # tutorial is a valid standalone command
        known_ungrouped = {"tutorial"}
        actual_ungrouped = ungrouped - known_ungrouped
        assert not actual_ungrouped, (
            f"Defined commands missing from command_groups: {sorted(actual_ungrouped)}"
        )


# ── REPO_URL ─────────────────────────────────────────────────────────

class TestRepoLinks:
    """Verify GitHub links in the manual point to real files in the repo."""

    EXPECTED_FILES = [
        "README.md",
        "design/endpoints.md",
        "AUTHENTICATION.md",
        "DATABASE_MANAGEMENT.md",
    ]

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_linked_file_exists(self, filename):
        """Each file referenced by a GitHub link must exist locally."""
        repo_root = os.path.join(os.path.dirname(__file__), "..")
        filepath = os.path.join(repo_root, filename)
        assert os.path.exists(filepath), (
            f"Manual links to '{filename}' but file doesn't exist"
        )

    def test_repo_url_present_in_manual(self, xts_data):
        """Manual command block should define REPO_URL."""
        manual_cmd = xts_data["manual"]["command"]
        assert "REPO_URL=" in manual_cmd, "REPO_URL variable not found in manual command"
        assert "https://github.com/rdkcentral/xts_allocator_server" in manual_cmd, (
            "Canonical rdkcentral GitHub URL not found in manual command"
        )


class TestLegacyCommandRegression:
    """Prevent regressions to previously fixed broken command references."""

    @pytest.mark.parametrize(
        "removed_command",
        [
            "xts allocator test_heartbeat",
            "xts allocator export_raft",
            "xts allocator export_python_raft",
        ],
    )
    def test_removed_commands_not_referenced(self, xts_raw, removed_command):
        assert removed_command not in xts_raw, (
            f"Found removed legacy command reference: {removed_command}"
        )
