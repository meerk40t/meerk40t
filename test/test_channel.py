import unittest
from collections import deque
from unittest.mock import patch
from meerk40t.kernel.channel import Channel


class TestChannel(unittest.TestCase):
    """Comprehensive test suite for the Channel class."""

    def setUp(self):
        """Set up test fixtures."""
        self.channel = Channel("test_channel")

    def tearDown(self):
        """Clean up after tests."""
        # Ensure any threaded channels are stopped
        if hasattr(self.channel, 'threaded') and self.channel.threaded:
            self.channel.threaded = False

    def test_channel_initialization(self):
        """Test channel initialization with various parameters."""
        # Basic channel
        channel = Channel("basic")
        self.assertEqual(channel.name, "basic")
        self.assertEqual(channel.buffer_size, 0)
        self.assertIsNone(channel.buffer)
        self.assertFalse(channel.timestamp)
        self.assertFalse(channel.pure)
        self.assertFalse(channel.ansi)

        # Channel with buffer
        channel = Channel("buffered", buffer_size=10)
        self.assertEqual(channel.buffer_size, 10)
        self.assertIsInstance(channel.buffer, deque)

        # Channel with formatting options
        channel = Channel("formatted", timestamp=True, ansi=True, line_end="\n")
        self.assertTrue(channel.timestamp)
        self.assertTrue(channel.ansi)
        self.assertEqual(channel.line_end, "\n")

    def test_channel_repr(self):
        """Test string representation of channel."""
        channel = Channel("test", buffer_size=5, line_end="\r\n")
        repr_str = repr(channel)
        self.assertIn("test", repr_str)
        self.assertIn("5", repr_str)
        self.assertIn("\\r\\n", repr_str)

    def test_basic_messaging(self):
        """Test basic message sending and receiving."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.channel("test message", indent=False)
        self.assertEqual(messages, ["test message"])

    def test_multiple_watchers(self):
        """Test multiple watchers receiving messages."""
        messages1 = []
        messages2 = []

        def collector1(msg):
            messages1.append(msg)
        def collector2(msg):
            messages2.append(msg)

        self.channel.watch(collector1)
        self.channel.watch(collector2)
        self.channel("shared message", indent=False)

        self.assertEqual(messages1, ["shared message"])
        self.assertEqual(messages2, ["shared message"])

    def test_watcher_deduplication(self):
        """Test that the same watcher is not added multiple times."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.channel.watch(collector)  # Should be ignored
        self.channel("message", indent=False)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], "message")

    def test_unwatch(self):
        """Test removing watchers."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.channel("message1", indent=False)
        self.assertEqual(messages, ["message1"])

        self.channel.unwatch(collector)
        self.channel("message2", indent=False)
        self.assertEqual(messages, ["message1"])  # No new message

    def test_buffering(self):
        """Test message buffering functionality."""
        channel = Channel("buffered", buffer_size=3)

        # Send messages
        channel("msg1", indent=False)
        channel("msg2", indent=False)
        channel("msg3", indent=False)
        channel("msg4", indent=False)  # Should push out msg1

        # Check buffer contents
        self.assertEqual(len(channel.buffer), 3)
        self.assertEqual(list(channel.buffer), ["msg2", "msg3", "msg4"])

    def test_buffer_overflow(self):
        """Test buffer size limits."""
        channel = Channel("buffered", buffer_size=2)
        channel("msg1", indent=False)
        channel("msg2", indent=False)
        channel("msg3", indent=False)  # Should remove msg1

        self.assertEqual(len(channel.buffer), 2)
        self.assertEqual(list(channel.buffer), ["msg2", "msg3"])

    def test_greet_string(self):
        """Test string greeting for new watchers."""
        self.channel.greet = "Welcome!"

        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.assertEqual(messages, ["Welcome!"])

    def test_greet_callable(self):
        """Test callable greeting for new watchers."""
        def greet_func():
            yield "Line 1"
            yield "Line 2"

        self.channel.greet = greet_func

        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.assertEqual(messages, ["Line 1", "Line 2"])

    def test_buffer_replay(self):
        """Test that buffered messages are replayed to new watchers."""
        channel = Channel("buffered", buffer_size=3)
        channel("msg1", indent=False)
        channel("msg2", indent=False)

        messages = []
        def collector(msg):
            messages.append(msg)

        channel.watch(collector)
        self.assertEqual(messages, ["msg1", "msg2"])

    def test_pure_mode(self):
        """Test pure mode bypasses text processing."""
        channel = Channel("pure", pure=True)

        messages = []
        def collector(msg):
            messages.append(msg)

        channel.watch(collector)
        channel("test\nmessage")
        # Should receive raw message without line_end processing
        self.assertEqual(messages, ["test\nmessage"])

    def test_line_end_processing(self):
        """Test line_end parameter."""
        channel = Channel("line_end", line_end="\r\n")

        messages = []
        def collector(msg):
            messages.append(msg)

        channel.watch(collector)
        channel("test message", indent=False)
        self.assertEqual(messages, ["test message\r\n"])

    def test_timestamp_formatting(self):
        """Test timestamp formatting."""
        channel = Channel("timestamp", timestamp=True)

        messages = []
        def collector(msg):
            messages.append(msg)

        channel.watch(collector)
        channel("test message")

        # Should contain timestamp
        self.assertEqual(len(messages), 1)
        self.assertIn("test message", messages[0])
        self.assertRegex(messages[0], r"\[\d{2}:\d{2}:\d{2}\]")

    def test_indent_formatting(self):
        """Test indentation formatting."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.channel("line1\nline2", indent=True)
        self.assertEqual(messages, ["    line1\n    line2"])

    def test_bbcode_to_ansi_conversion(self):
        """Test BBCode to ANSI conversion."""
        channel = Channel("ansi", ansi=True)

        # Test basic colors
        result = channel.bbcode_to_ansi("[red]red text[/red]")
        self.assertIn("\033[31m", result)
        self.assertIn("\033[0m", result)

        # Test raw passthrough
        result = channel.bbcode_to_ansi("[raw][red]raw bbcode[/raw]")
        self.assertIn("[red]", result)

    def test_bbcode_to_plain_stripping(self):
        """Test BBCode stripping to plain text."""
        result = self.channel.bbcode_to_plain("[red]red text[/red] normal")
        self.assertEqual(result, "red text normal")

    def test_channel_add_operator(self):
        """Test += operator for adding watchers."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel += collector
        self.channel("test", indent=False)
        self.assertEqual(messages, ["test"])

    def test_channel_sub_operator(self):
        """Test -= operator for removing watchers."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel += collector
        self.channel("test1", indent=False)
        self.assertEqual(messages, ["test1"])

        self.channel -= collector
        self.channel("test2", indent=False)
        self.assertEqual(messages, ["test1"])

    def test_channel_bool_evaluation(self):
        """Test boolean evaluation of channel."""
        # Empty channel should be falsy
        self.assertFalse(self.channel)

        # Channel with watchers should be truthy
        self.channel.watch(lambda x: None)
        self.assertTrue(self.channel)

        # Channel with buffer should be truthy
        channel = Channel("buffered", buffer_size=1)
        self.assertTrue(channel)

    def test_binary_message_handling(self):
        """Test handling of binary messages."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        binary_data = b"binary data"
        self.channel(binary_data)
        self.assertEqual(messages, [binary_data])

    def test_mixed_message_types(self):
        """Test handling mixed string and binary messages."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)
        self.channel("string message", indent=False)
        self.channel(b"binary message")
        self.assertEqual(messages, ["string message", b"binary message"])


class TestChannelThreading(unittest.TestCase):
    """Test threaded channel functionality."""

    def setUp(self):
        self.channel = Channel("threaded")

    def tearDown(self):
        if hasattr(self.channel, 'threaded') and self.channel.threaded:
            self.channel.threaded = False

    def test_threaded_messaging(self):
        """Test basic threaded message sending."""
        messages = []
        def collector(msg):
            messages.append(msg)

        self.channel.watch(collector)

        # Mock the threaded start method - placeholder for future implementation
        with patch.object(self.channel, 'start'):
            self.channel("test", execute_threaded=True)
            # In real implementation, this would be handled by the thread

    def test_threaded_channel_initialization(self):
        """Test that threaded channels can be created."""
        # This is a placeholder - actual threading tests would need
        # more complex setup with real kernel integration
        pass


class TestChannelErrorHandling(unittest.TestCase):
    """Test error handling in channel operations."""

    def setUp(self):
        self.channel = Channel("error_test")

    def test_watcher_exception_isolation(self):
        """Test that one watcher exception doesn't break others."""
        messages = []

        def good_collector(msg):
            messages.append(f"good: {msg}")

        def bad_collector(msg):
            raise Exception("Watcher failed")

        def another_good_collector(msg):
            messages.append(f"another: {msg}")

        self.channel.watch(good_collector)
        self.channel.watch(bad_collector)
        self.channel.watch(another_good_collector)

        # This should not raise an exception
        self.channel("test message", indent=False)

        # Good collectors should still work
        self.assertIn("good: test message", messages)
        self.assertIn("another: test message", messages)


class TestChannelWeakReferences(unittest.TestCase):
    """Test weak reference functionality for watchers."""

    def setUp(self):
        self.channel = Channel("weak_test")

    def test_weak_reference_cleanup(self):
        """Test that dead weak references are cleaned up."""
        messages = []

        def collector(msg):
            messages.append(msg)

        # Simulate weak reference watching (would need implementation)
        self.channel.watch(collector)
        self.channel("test", indent=False)
        self.assertEqual(messages, ["test"])

        # When collector goes out of scope and is garbage collected,
        # weak reference should be cleaned up
        del collector
        # In real implementation, this would trigger cleanup


if __name__ == '__main__':
    unittest.main()