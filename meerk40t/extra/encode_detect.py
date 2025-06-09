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
    BOM_UTF_8 = "\xef\xbb\xbf"
    BOM_UTF_16_BE = "\xfe\xff"
    BOM_UTF_16_LE = "\xff\xfe"

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

        # test 3 byte UTF-8 BOM
        file_data += fh.read(1)
        # print(f"first 3 bytes: {file_data}")
        if file_data == EncodingDetectFile.BOM_UTF_8:
            return result(
                EncodingDetectFile.ENCODING_UTF_8, EncodingDetectFile.BOM_UTF_8
            )

        # no BOM marker - return bytes read so far
        return False, False, file_data

    def _detect_ascii_utf8(self, file_data):
        ascii_chars_only = True

        byte_follow = 0
        for file_byte in file_data:
            # process additional character byte(s)
            if byte_follow:
                if 128 <= file_byte <= 191:
                    byte_follow -= 1
                    ascii_chars_only = False
                    continue

                # not ASCII or UTF-8
                return False

            # determine byte length of character
            # https://en.wikipedia.org/wiki/UTF-8#Codepage_layout
            if 1 <= file_byte <= 127:
                # single byte
                continue

            if 194 <= file_byte <= 223:
                # one byte follows
                byte_follow = 1
                continue

            if 224 <= file_byte <= 239:
                # two bytes follow
                byte_follow = 2
                continue

            if 240 <= file_byte <= 244:
                # three bytes follow
                byte_follow = 3
                continue

            # not ASCII or UTF-8
            return EncodingDetectFile.ENCODING_CP1252

        # end of file data [byte_follow] must be zero to ensure last character was consumed
        if byte_follow:
            return False

        # success - return ASCII or UTF-8 result
        return (
            EncodingDetectFile.ENCODING_ASCII
            if (ascii_chars_only)
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
            fh = open(file_path, "rb")
        except Exception:
            return False

        # detect a byte order mark (BOM)
        file_encoding, bom_marker, file_data = self._detect_bom(fh)
        if file_encoding:
            # file has a BOM - decode everything past it
            try:
                decode = fh.read().decode(file_encoding)
            except UnicodeDecodeError:
                return False
            # print(f"decoded: {decode}")
            fh.close()

            return (file_encoding, bom_marker, decode)

        # no BOM - read remaining file data
        file_data += fh.read()
        #  print(f"All bytes: {file_data}")
        fh.close()

        # test for ASCII/UTF-8
        file_encoding = self._detect_ascii_utf8(file_data)
        if file_encoding:
            # file is ASCII or UTF-8 (without BOM)
            return (file_encoding, None, file_data.decode(file_encoding))

        # test for UTF-16
        file_encoding = self._detect_utf16(file_data)
        if file_encoding:
            # file is UTF-16(-like) (without BOM)
            return (file_encoding, None, file_data.decode(file_encoding))

        # can't determine encoding
        return False
