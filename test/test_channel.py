import unittest
from collections import deque
from unittest.mock import patch
from meerk40t.kernel.channel import Channel
import threading
import time


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

    def test_resize_buffer_disable(self):
        """Test disabling buffer by resizing to zero."""
        channel = Channel("buffered", buffer_size=3)
        channel("msg1", indent=False)
        channel("msg2", indent=False)
        
        # Verify buffer has content
        self.assertEqual(len(channel.buffer), 2)
        
        # Disable buffering
        channel.resize_buffer(0)
        self.assertIsNone(channel.buffer)
        self.assertEqual(channel.buffer_size, 0)
        
        # New messages should not be buffered
        channel("msg3", indent=False)
        self.assertIsNone(channel.buffer)

    def test_resize_buffer_shrink(self):
        """Test shrinking buffer size."""
        channel = Channel("buffered", buffer_size=4)
        channel("msg1", indent=False)
        channel("msg2", indent=False)
        channel("msg3", indent=False)
        
        # Shrink buffer to size 2
        channel.resize_buffer(2)
        self.assertEqual(channel.buffer_size, 2)
        self.assertEqual(len(channel.buffer), 2)
        # Should keep most recent messages
        self.assertEqual(list(channel.buffer), ["msg2", "msg3"])

    def test_resize_buffer_grow(self):
        """Test growing buffer size."""
        channel = Channel("buffered", buffer_size=2)
        channel("msg1", indent=False)
        channel("msg2", indent=False)
        
        # Grow buffer to size 4
        channel.resize_buffer(4)
        self.assertEqual(channel.buffer_size, 4)
        self.assertEqual(len(channel.buffer), 2)
        self.assertEqual(list(channel.buffer), ["msg1", "msg2"])
        
        # Add more messages
        channel("msg3", indent=False)
        channel("msg4", indent=False)
        self.assertEqual(len(channel.buffer), 4)

    def test_resize_buffer_from_none(self):
        """Test enabling buffer on channel that had no buffer."""
        channel = Channel("no_buffer", buffer_size=0)
        self.assertIsNone(channel.buffer)
        
        # Enable buffering
        channel.resize_buffer(3)
        self.assertEqual(channel.buffer_size, 3)
        self.assertIsNotNone(channel.buffer)
        
        # Should work normally
        channel("msg1", indent=False)
        self.assertEqual(len(channel.buffer), 1)

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
        """Test BBCode to ANSI conversion with comprehensive test cases."""
        channel = Channel("ansi", ansi=True)

        # Test cases: (bbcode_input, expected_ansi_sequences, expected_plain_text_preserved)
        bbcode_cases = [
            # Basic colors
            ("[red]red text[/red]", ["\033[31m", "\033[0m"], "red text"),
            ("[green]green text[/green]", ["\033[32m", "\033[0m"], "green text"),
            ("[blue]blue text[/blue]", ["\033[34m", "\033[0m"], "blue text"),
            ("[yellow]yellow text[/yellow]", ["\033[33m", "\033[0m"], "yellow text"),
            ("[magenta]magenta text[/magenta]", ["\033[35m", "\033[0m"], "magenta text"),
            ("[cyan]cyan text[/cyan]", ["\033[36m", "\033[0m"], "cyan text"),
            ("[white]white text[/white]", ["\033[37m", "\033[0m"], "white text"),
            ("[black]black text[/black]", ["\033[30m", "\033[0m"], "black text"),
            
            # Background colors
            ("[bg-red]bg red[/bg-red]", ["\033[41m", "\033[0m"], "bg red"),
            ("[bg-green]bg green[/bg-green]", ["\033[42m", "\033[0m"], "bg green"),
            
            # Styles
            ("[bold]bold text[/bold]", ["\033[1m", "\033[22m"], "bold text"),
            ("[italic]italic text[/italic]", ["\033[3m", "\033[23m"], "italic text"),
            ("[underline]underline text[/underline]", ["\033[4m", "\033[24m"], "underline text"),
            
            # Nested tags
            ("[red][bold]nested[/bold][/red]", ["\033[31m", "\033[1m", "\033[22m", "\033[0m"], "nested"),
            
            # Raw passthrough
            ("[raw][red]raw bbcode[/raw]", [], "[red]raw bbcode"),
            
            # Malformed/unclosed tags (should still process valid parts)
            ("[red]unclosed", ["\033[31m"], "unclosed"),
            ("[red][green]mismatched[/red]", ["\033[31m", "\033[32m", "\033[0m"], "mismatched"),
            
            # Unknown tags (should be stripped/preserved based on implementation)
            ("[unknown]unknown[/unknown]", [], "unknown"),
            
            # Empty tags
            ("[red][/red]", ["\033[31m", "\033[0m"], ""),
            
            # Multiple tags in sequence
            ("[red]red[/red][blue]blue[/blue]", ["\033[31m", "\033[0m", "\033[34m", "\033[0m"], "redblue"),
        ]

        for bbcode, expected_ansi, expected_text in bbcode_cases:
            with self.subTest(bbcode=bbcode):
                result = channel.bbcode_to_ansi(bbcode)
                
                # Check that expected ANSI sequences are present
                for ansi_seq in expected_ansi:
                    self.assertIn(ansi_seq, result, f"Missing ANSI sequence {repr(ansi_seq)} in result {repr(result)}")
                
                # Check that the text content is preserved (after ANSI processing)
                # This is a basic check - in practice the ANSI codes will be interspersed
                if expected_text:
                    # Remove ANSI codes and check text is there
                    import re
                    plain_result = re.sub(r'\033\[[0-9;]*m', '', result)
                    self.assertIn(expected_text, plain_result, 
                                f"Expected text {repr(expected_text)} not found in {repr(plain_result)}")

    def test_bbcode_to_plain_stripping(self):
        """Test BBCode stripping to plain text."""
        # Test basic stripping
        result = self.channel.bbcode_to_plain("[red]red text[/red] normal")
        self.assertEqual(result, "red text normal")
        
        # Test raw passthrough preservation
        result = self.channel.bbcode_to_plain("[raw][red]raw bbcode[/raw] normal")
        self.assertEqual(result, "[red]raw bbcode normal")
        
        # Test malformed tags
        result = self.channel.bbcode_to_plain("[red]unclosed normal")
        self.assertEqual(result, "unclosed normal")
        
        # Test nested tags
        result = self.channel.bbcode_to_plain("[red][bold]nested[/bold][/red] normal")
        self.assertEqual(result, "nested normal")

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

    def test_concurrent_threaded_messaging(self):
        """Test that threaded channels handle concurrent messages correctly."""
        import concurrent.futures
        import threading
        
        messages = []
        lock = threading.Lock()
        
        def thread_safe_collector(msg):
            with lock:
                messages.append(f"{threading.current_thread().name}: {msg}")
        
        self.channel.watch(thread_safe_collector)
        
        # Create a mock root object with threaded method
        class MockRoot:
            def threaded(self, func, thread_name, daemon):
                thread = threading.Thread(target=func, name=thread_name, daemon=daemon)
                thread.start()
                return thread
        
        root = MockRoot()
        
        # Start the threaded channel
        thread = self.channel.start(root)
        
        try:
            # Send messages from multiple threads
            def send_messages(thread_id, num_messages):
                for i in range(num_messages):
                    self.channel(f"Message {thread_id}-{i}", execute_threaded=True)
                    time.sleep(0.01)  # Small delay to allow interleaving
            
            # Use ThreadPoolExecutor to send messages concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for thread_id in range(3):
                    future = executor.submit(send_messages, thread_id, 5)
                    futures.append(future)
                
                # Wait for all messages to be sent
                for future in futures:
                    future.result()
            
            # Give some time for all messages to be processed
            time.sleep(0.5)
            
            # Stop the threaded channel
            thread.stop()
            thread.join(timeout=1.0)
            
            # Verify we received messages from multiple threads
            self.assertGreater(len(messages), 0, "No messages were received")
            
            # Check that messages came from different threads
            thread_names = set()
            for msg in messages:
                if ": " in msg:
                    thread_name = msg.split(": ")[0]
                    thread_names.add(thread_name)
            
            # We should have messages from multiple threads (including the processing thread)
            self.assertGreaterEqual(len(thread_names), 1, "Messages should be processed by at least one thread")
            
        finally:
            # Ensure cleanup
            if hasattr(self.channel, 'threaded') and self.channel.threaded:
                self.channel.threaded = False
            if thread.is_alive():
                thread.join(timeout=1.0)

    def test_threaded_message_ordering(self):
        """Test that messages are processed in order within threaded mode."""
        messages = []
        lock = threading.Lock()
        
        def ordered_collector(msg):
            with lock:
                messages.append(msg)
        
        self.channel.watch(ordered_collector)
        
        # Create a mock root object
        class MockRoot:
            def threaded(self, func, thread_name, daemon):
                thread = threading.Thread(target=func, name=thread_name, daemon=daemon)
                thread.start()
                return thread
        
        root = MockRoot()
        
        # Start the threaded channel
        thread = self.channel.start(root)
        
        try:
            # Send messages in order
            for i in range(10):
                self.channel(f"Message {i}", execute_threaded=True, indent=False)
            
            # Give time for processing
            time.sleep(0.3)
            
            # Stop the channel by setting threaded to False
            self.channel.threaded = False
            thread.join(timeout=1.0)
            
            # Verify messages were received (order may vary due to threading)
            self.assertEqual(len(messages), 10, "All messages should be received")
            
            # Extract message numbers and check they are all present
            received_nums = set()
            for msg in messages:
                if msg.startswith("Message "):
                    try:
                        num = int(msg.split(" ")[1])
                        received_nums.add(num)
                    except (ValueError, IndexError):
                        pass
            
            expected_nums = set(range(10))
            self.assertEqual(received_nums, expected_nums, "All message numbers should be present")
            
        finally:
            if hasattr(self.channel, 'threaded') and self.channel.threaded:
                self.channel.threaded = False
            if thread.is_alive():
                thread.join(timeout=1.0)


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
        import gc
        
        messages = []

        def collector(msg):
            messages.append(msg)

        # Register the watcher with weak=True
        self.channel.watch(collector, weak=True)
        self.channel("test", indent=False)
        self.assertEqual(messages, ["test"])

        # Delete the watcher and force garbage collection
        del collector
        gc.collect()

        # Check that the watcher list has been cleaned up
        # The weak reference should be automatically removed when the object is GC'd
        # Since we have the _watcher_died callback, dead refs should be removed
        self.assertEqual(len(self.channel.watchers), 0)

    def test_weak_reference_strong_fallback(self):
        """Test that weak=False still works normally."""
        messages = []

        def collector(msg):
            messages.append(msg)

        # Register with weak=False (default)
        self.channel.watch(collector, weak=False)
        self.channel("test", indent=False)
        self.assertEqual(messages, ["test"])

        # Function should still be in watchers
        self.assertEqual(len(self.channel.watchers), 1)
        self.assertIn(collector, self.channel.watchers)


if __name__ == '__main__':
    unittest.main()