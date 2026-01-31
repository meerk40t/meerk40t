"""
Try to detect some common encoding patterns.
Based on https://github.com/magnetikonline/py-encoding-detect

It will detect the following encodings of a text file:

    ASCII
    UTF-8
    UTF-16BE
    UTF-16LE

"""


class EncodingDetectFile:
    ENCODING_ASCII = "ascii"
    ENCODING_CP1252 = "cp1252"
    ENCODING_UTF_8 = "utf_8"
    ENCODING_UTF_16_BE = "utf_16_be"
    ENCODING_UTF_16_LE = "utf_16_le"

    # http://unicode.org/faq/utf_bom.html#BOM
    BOM_UTF_8 = b"\xef\xbb\xbf"
    BOM_UTF_16_BE = b"\xfe\xff"
    BOM_UTF_16_LE = b"\xff\xfe"

    BYTE_EOL = (13, 10)  # \r\n

    UTF_16_NULL_PERCENT_POSITIVE = 0.7
    UTF_16_NULL_PERCENT_NEGATIVE = 0.1

    def _detect_bom(self, fh):
        def result(encoding, bom_marker):
            return (encoding, bom_marker, None)

        # test 2 byte UTF-16 BOMs
        file_data = fh.read(2)
        # print(f"first 2 bytes: {file_data}")
        if file_data == EncodingDetectFile.BOM_UTF_16_BE:
            return result(
                EncodingDetectFile.ENCODING_UTF_16_BE, EncodingDetectFile.BOM_UTF_16_BE
            )

        if file_data == EncodingDetectFile.BOM_UTF_16_LE:
            return result(
                EncodingDetectFile.ENCODING_UTF_16_LE, EncodingDetectFile.BOM_UTF_16_LE
            )

        # test 3 byte UTF-8 BOM (only if we have at least 3 bytes available)
        if len(file_data) == 2:
            file_data += fh.read(1)
            if len(file_data) == 3 and file_data == EncodingDetectFile.BOM_UTF_8:
                return result(
                    EncodingDetectFile.ENCODING_UTF_8, EncodingDetectFile.BOM_UTF_8
                )

        # no BOM marker - return bytes read so far
        return False, False, file_data

    def _detect_ascii_utf8(self, file_data):
        ascii_chars_only = True
        i = 0

        while i < len(file_data):
            file_byte = file_data[i]

            # determine byte length of character
            # https://en.wikipedia.org/wiki/UTF-8#Codepage_layout
            if 1 <= file_byte <= 127:
                # single byte ASCII
                i += 1
                continue

            if 194 <= file_byte <= 223:
                # two bytes follow (2-byte sequence)
                if i + 1 >= len(file_data):
                    return False  # incomplete sequence
                second_byte = file_data[i + 1]
                if not (128 <= second_byte <= 191):
                    return False  # invalid continuation byte

                # check for overlong encoding (should have been 1 byte)
                if file_byte == 194 and second_byte <= 191:
                    return False  # overlong encoding

                ascii_chars_only = False
                i += 2
                continue

            if 224 <= file_byte <= 239:
                # three bytes follow (3-byte sequence)
                if i + 2 >= len(file_data):
                    return False  # incomplete sequence
                second_byte = file_data[i + 1]
                third_byte = file_data[i + 2]
                if not (128 <= second_byte <= 191 and 128 <= third_byte <= 191):
                    return False  # invalid continuation bytes

                # check for overlong encoding (should have been 2 bytes or less)
                if file_byte == 224 and second_byte <= 159:
                    return False  # overlong encoding

                ascii_chars_only = False
                i += 3
                continue

            if 240 <= file_byte <= 244:
                # four bytes follow (4-byte sequence)
                if i + 3 >= len(file_data):
                    return False  # incomplete sequence
                second_byte = file_data[i + 1]
                third_byte = file_data[i + 2]
                fourth_byte = file_data[i + 3]
                if not (128 <= second_byte <= 191 and 128 <= third_byte <= 191 and 128 <= fourth_byte <= 191):
                    return False  # invalid continuation bytes

                # check for overlong encoding (should have been 3 bytes or less)
                if file_byte == 240 and second_byte <= 143:
                    return False  # overlong encoding

                ascii_chars_only = False
                i += 4
                continue

            # invalid UTF-8 leading byte (128-193, 245-255)
            return False

        # success - return ASCII or UTF-8 result
        return (
            EncodingDetectFile.ENCODING_ASCII
            if ascii_chars_only
            else EncodingDetectFile.ENCODING_UTF_8
        )

    def _detect_utf16(self, file_data):
        null_byte_odd, null_byte_even = 0, 0
        eol_odd, eol_even = 0, 0

        odd_byte = None
        for file_byte in file_data:
            # build pairs of bytes
            if odd_byte is None:
                odd_byte = file_byte
                continue

            # look for odd/even null byte and check other byte for EOL
            if odd_byte == 0:
                null_byte_odd += 1
                if file_byte in EncodingDetectFile.BYTE_EOL:
                    eol_even += 1

            elif file_byte == 0:
                null_byte_even += 1
                if odd_byte in EncodingDetectFile.BYTE_EOL:
                    eol_odd += 1

            odd_byte = None

        # attempt detection based on line endings
        if (not eol_odd) and eol_even:
            return EncodingDetectFile.ENCODING_UTF_16_BE

        if eol_odd and (not eol_even):
            return EncodingDetectFile.ENCODING_UTF_16_LE

        # can't detect on line endings - evaluate ratio of null bytes in odd/even positions
        # this will give an indication of how much ASCII (1-127) level text is present
        data_size_half = len(file_data) / 2
        threshold_positive = int(
            data_size_half * EncodingDetectFile.UTF_16_NULL_PERCENT_POSITIVE
        )
        threshold_negative = int(
            data_size_half * EncodingDetectFile.UTF_16_NULL_PERCENT_NEGATIVE
        )

        # must have enough file data to have value ([threshold_positive] must be non-zero)
        if threshold_positive:
            if (null_byte_odd > threshold_positive) and (
                null_byte_even < threshold_negative
            ):
                return EncodingDetectFile.ENCODING_UTF_16_BE

            if (null_byte_odd < threshold_negative) and (
                null_byte_even > threshold_positive
            ):
                return EncodingDetectFile.ENCODING_UTF_16_LE

        # not UTF-16 - or insufficient data to determine with confidence
        return False

    def load(self, file_path):
        # open file
        try:
            with open(file_path, "rb") as fh:
                # detect a byte order mark (BOM)
                file_encoding, bom_marker, file_data = self._detect_bom(fh)
                if file_encoding:
                    # file has a BOM - decode everything past it
                    try:
                        remaining_data = fh.read()
                        decoded = remaining_data.decode(file_encoding)
                        return (file_encoding, bom_marker, decoded)
                    except UnicodeDecodeError:
                        return False

                # no BOM - read remaining file data
                file_data += fh.read()

        except (OSError, IOError):
            # File cannot be opened or read
            return False

        #  print(f"All bytes: {file_data}")

        # test for ASCII/UTF-8
        file_encoding = self._detect_ascii_utf8(file_data)
        if file_encoding:
            # file is ASCII or UTF-8 (without BOM)
            try:
                return (file_encoding, None, file_data.decode(file_encoding))
            except UnicodeDecodeError:
                return False

        # test for UTF-16
        file_encoding = self._detect_utf16(file_data)
        if file_encoding:
            # file is UTF-16(-like) (without BOM)
            try:
                return (file_encoding, None, file_data.decode(file_encoding))
            except UnicodeDecodeError:
                return False

        # can't determine encoding
        return False
