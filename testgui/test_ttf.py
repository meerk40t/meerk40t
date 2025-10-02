#!/usr/bin/env python3
"""
Comprehensive test script for TTF parser improvements.
Tests robustness, error handling, variation sequences, and performance.
"""

import os
import sys
import time
import traceback
from pathlib import Path

# Add meerk40t to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "meerk40t"))

from meerk40t.tools.ttfparser import TrueTypeFont


def find_test_fonts():
    """Find available TTF fonts for testing."""
    font_paths = []

    # Common Windows font directories
    windows_fonts = [
        "C:/Windows/Fonts",
        "C:/Windows/System32/Fonts",
        os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
        # "c:/temp/fonts", # Example custom path for testing
    ]

    # Common Linux font directories
    linux_fonts = ["/usr/share/fonts", "/usr/local/share/fonts", "~/.fonts"]

    # Common macOS font directories
    macos_fonts = ["/System/Library/Fonts", "/Library/Fonts", "~/Library/Fonts"]

    all_paths = windows_fonts + linux_fonts + macos_fonts

    for font_dir in all_paths:
        try:
            font_path = Path(font_dir).expanduser()
            if font_path.exists():
                for font_file in font_path.rglob("*.ttf"):
                    if font_file.is_file():
                        font_paths.append(str(font_file))
                        # if len(font_paths) >= 10:  # Limit for testing
                        #     return font_paths
        except (OSError, PermissionError):
            continue

    return font_paths


def test_basic_parsing(font_path):
    """Test basic font parsing functionality."""
    print(f"\n=== Testing Basic Parsing: {os.path.basename(font_path)} ===")

    try:
        start_time = time.time()
        font = TrueTypeFont(font_path)
        parse_time = time.time() - start_time

        print(f"✓ Successfully parsed in {parse_time:.3f}s")
        print(f"  Font Family: {font.font_family}")
        print(f"  Font Subfamily: {font.font_subfamily}")
        print(f"  Font Name: {font.font_name}")
        print(f"  Units per EM: {font.units_per_em}")
        print(f"  Number of glyphs: {len(font.glyphs)}")
        print(
            f"  Character map size: {len(font._character_map)} (type: {font.cmap_version})"
        )
        print(f"  Variation sequences: {len(font._variation_sequences)}")
        print(f"  Horizontal metrics: {len(font.horizontal_metrics)}")

        return True, font, parse_time

    except Exception as e:
        print(f"✗ Failed to parse: {e}")
        traceback.print_exc()
        return False, None, 0


def test_character_lookup(font):
    """Test character lookup functionality."""
    print("\n--- Testing Character Lookup ---")

    test_chars = ["A", "a", "0", "!", "€", "中", "🙂"]

    for char in test_chars:
        try:
            glyph_id = font.get_glyph_index(char)
            print(f"  '{char}' (U+{ord(char):04X}) -> glyph {glyph_id}")
        except Exception as e:
            print(f"  '{char}' -> Error: {e}")


def test_variation_sequences(font):
    """Test Unicode variation sequence support."""
    print("\n--- Testing Variation Sequences ---")

    if hasattr(font, "_variation_sequences") and font._variation_sequences:
        print(f"  Found {len(font._variation_sequences)} variation sequences:")
        count = 0
        for (base_char, vs), glyph_id in font._variation_sequences.items():
            if count < 5:  # Show first 5
                print(f"    U+{base_char:04X} + U+{vs:04X} -> glyph {glyph_id}")
                count += 1
        if len(font._variation_sequences) > 5:
            print(
                f"    ... and {len(font._variation_sequences) - 5} more"
            )  # Test lookup with variation sequences
            if hasattr(font, "lookup_glyph_with_variation"):
                try:
                    # Test with first variation sequence
                    first_vs = next(iter(font._variation_sequences.keys()))
                    base_char, vs = first_vs
                    result = font.lookup_glyph_with_variation(chr(base_char), vs)
                    print(
                        f"  Variation lookup test: U+{base_char:04X} + U+{vs:04X} -> glyph {result}"
                    )
                except Exception as e:
                    print(f"  Variation lookup test failed: {e}")
        return True
    print("  No variation sequences found in this font")
    return False


def test_error_handling():
    """Test error handling with invalid files."""
    print("\n=== Testing Error Handling ===")

    # Test with non-existent file
    try:
        TrueTypeFont("nonexistent_font.ttf")
        print("✗ Should have failed with non-existent file")
    except Exception as e:
        print(f"✓ Correctly handled non-existent file: {type(e).__name__}")

    # Test with invalid file (create a dummy file)
    invalid_path = "test_invalid.ttf"
    try:
        with open(invalid_path, "wb") as f:
            f.write(b"This is not a TTF file")

        TrueTypeFont(invalid_path)
        print("✗ Should have failed with invalid file")
    except Exception as e:
        print(f"✓ Correctly handled invalid file: {type(e).__name__}")
    finally:
        if os.path.exists(invalid_path):
            os.remove(invalid_path)


def test_performance_stress():
    """Test performance with repeated operations."""
    print("\n=== Testing Performance ===")

    fonts = find_test_fonts()
    if not fonts:
        print("No fonts found for performance testing")
        return

    # Test parsing multiple fonts
    total_time = 0
    successful_parses = 0

    for font_path in fonts[:5]:  # Test first 5 fonts
        try:
            start_time = time.time()
            font = TrueTypeFont(font_path)
            parse_time = time.time() - start_time
            total_time += parse_time
            successful_parses += 1

            # Test character lookups
            lookup_start = time.time()
            for i in range(100):  # 100 lookups
                font.get_glyph_index(chr(65 + (i % 26)))  # A-Z
            lookup_time = time.time() - lookup_start

            print(
                f"  {os.path.basename(font_path)}: parse={parse_time:.3f}s, 100 lookups={lookup_time:.3f}s"
            )

        except Exception as e:
            print(f"  {os.path.basename(font_path)}: Failed - {e}")

    if successful_parses > 0:
        avg_time = total_time / successful_parses
        print(f"\nAverage parse time: {avg_time:.3f}s ({successful_parses} fonts)")


def test_debug_features(font):
    """Test debug and inspection features."""
    print("\n--- Testing Debug Features ---")

    # Test debug methods if they exist
    if hasattr(font, "debug_variation_sequences"):
        try:
            font.debug_variation_sequences()
            print("  ✓ debug_variation_sequences() executed successfully")
        except Exception as e:
            print(f"  ✗ debug_variation_sequences() failed: {e}")

    # Test glyph data access
    try:
        if hasattr(font, "glyph_data") and font.glyph_data:
            print(f"  Glyph data available: {len(font.glyph_data)} entries")
            # Test first few glyphs
            for i in range(min(3, len(font.glyph_data))):
                glyph = font.glyph_data[i]
                if glyph:
                    print(f"    Glyph {i}: {len(glyph)} contours")
    except Exception as e:
        print(f"  Glyph data access failed: {e}")


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("=" * 60)
    print("TTF Parser Comprehensive Test Suite")
    print("=" * 60)

    # Find available fonts
    print("\nSearching for test fonts...")
    fonts = find_test_fonts()

    if not fonts:
        print("No TTF fonts found. Creating minimal test...")
        test_error_handling()
        return

    print(f"Found {len(fonts)} fonts for testing")

    # Test error handling first
    test_error_handling()

    # Test performance
    test_performance_stress()

    # Detailed testing on first few fonts
    print(f"\n{'=' * 60}")
    print("Detailed Feature Testing")
    print("=" * 60)

    tested_fonts = 0
    type_count = {}
    var_count = 0
    for font_path in fonts:
        # if tested_fonts >= 3:  # Limit detailed testing
        #     break

        success, font, parse_time = test_basic_parsing(font_path)
        if success and font:
            type_count[font.cmap_version] = type_count.get(font.cmap_version, 0) + 1
            test_character_lookup(font)
            if test_variation_sequences(font):
                var_count += 1
            test_debug_features(font)
            tested_fonts += 1

    print(f"\n{'=' * 60}")
    print("Test Suite Complete")
    print("=" * 60)
    print(f"Tested {tested_fonts} fonts in detail")
    print(f"Character map types found: {type_count}")
    print(f"Variation sequences found: {var_count}")
    print("Check output above for any errors or warnings")


if __name__ == "__main__":
    run_comprehensive_tests()
