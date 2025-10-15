import os

JHFPARSER_VERSION = "0.0.1"

"""
    The Hershey fonts are a collection of vector fonts developed c. 1967 by Dr. Allen Vincent Hershey at the Naval Weapons Laboratory,
    originally designed to be rendered using vectors on early cathode ray tube displays. Decomposing curves to connected straight lines
    allowed Hershey to produce complex typographic designs. In their original form the font data consists simply of a series of coordinates,
    meant to be connected by straight lines on the screen. The fonts are publicly available and have few usage restrictions.
    Vector fonts are easily scaled and rotated in two or three dimensions; consequently the Hershey fonts have been widely
    used in computer graphics, computer-aided design programs, and more recently also in computer-aided manufacturing
    applications like laser engraving. (https://en.wikipedia.org/wiki/Hershey_fonts)
"""

STD_FONT_FILE = "meerk40t.jhf"


class JhfPath:
    """
    Example path code. Any class with these functions would work as well. When render is called on the JhfFont class
    the path is given particular useful segments.
    """

    def __init__(self):
        self.path = list()

    def new_path(self):
        """
        Start of a new path.
        """
        self.path.append(None)

    def move(self, x, y):
        """
        Move current point to the point specified.
        """
        self.path.append((x, y))

    def line(self, x0, y0, x1, y1):
        """
        Draw a line from the current point to the specified point.
        """
        self.path.append((x0, y0, x1, y1))

    def character_end(self):
        pass


class JhfFont:
    """
    This class performs the parsing of the Hershey fonts in jhf (James Hull Format).
    Composing them into specific glyphs which consist of commands in a vector-shape language.
    When .render() is called on some text, vector actions are performed
    on the font which create the vector path.
    """

    def __init__(self, filename: str, glyph_data=None):
        self.STROKE_BASED = True
        self.type = "Hershey"
        self.glyphs = dict()  # Glyph dictionary
        tempstr = os.path.basename(filename)
        fname, fext = os.path.splitext(tempstr)
        self.valid = False
        self.active = True
        self.font_name = fname
        self._line_information = []
        if filename:
            self._parse(filename)

    def __str__(self):
        return f'{self.type}("{self.font_name}", glyphs: {len(self.glyphs)})'

    def line_information(self):
        return self._line_information

    @staticmethod
    def hershey_val(character):
        return ord(character) - ord("R")

    def _read_hershey_glyph(self, f, glyphindex):
        line = ""
        while line == "":
            line = f.readline()
            if (not line) or line == "\x1a":  # eof
                return False
            line = line.rstrip()
        return self._parse_glyph_line(line, glyphindex)

    def _parse_glyph_line(self, line, glyphindex):
        # read a Hershey format line
        glyphnum = int(line[0:5])  # glyphnum (junk in some .jhf files)
        nverts = int(line[5:8]) - 1
        leftpos = self.hershey_val(line[8])
        rightpos = self.hershey_val(line[9])
        vertchars = line[10:]
        nvertchars = len(vertchars)

        # join split lines in the Hershey data
        while nverts * 2 > nvertchars:
            nextline = f.readline().rstrip()
            line += nextline
            vertchars += nextline
            nvertchars = len(vertchars)
        if nverts * 2 != nvertchars:
            print(
                f"Parse Hershey Glyph: format error (nvertchars={nvertchars} not {2 * nverts})"
            )
        else:
            # print(f"Glyph, idx={glyphindex}, glyphnum={glyphnum}, left={leftpos}, right={rightpos}, vertices={nverts}")
            # Now we have one line with a full glyph definition
            idx = 0
            realleft = leftpos
            realright = rightpos
            realtop = 0
            realbottom = 0
            cidx = 0
            while idx < nverts:
                leftchar = vertchars[2 * idx]
                rightchar = vertchars[2 * idx + 1]
                if leftchar == " " and rightchar == "R":
                    # pen up
                    pass
                else:
                    leftval = self.hershey_val(leftchar)
                    rightval = self.hershey_val(rightchar)
                    if cidx == 0:
                        realleft = leftval
                        realright = leftval
                        realtop = rightval
                        realbottom = rightval
                    else:
                        if leftval < realleft:
                            realleft = leftval
                        if leftval > realright:
                            realright = leftval
                        if rightval < realtop:
                            realtop = rightval
                        if rightval > realbottom:
                            realbottom = rightval
                    cidx += 1
                idx += 1

            glyphchar = chr(glyphindex)
            struct = {
                "index": glyphindex,
                "num": glyphnum,
                "left": leftpos,  # what the glyph claims
                "right": rightpos,  # what the glyph claims
                "top": realtop,  # extension to the top
                "bottom": realbottom,  # extension to the bottom
                "realleft": realleft,  # the real extension
                "realright": realright,  # the real extension
                "nverts": nverts,
                "vertices": vertchars,
            }
            self.glyphs[glyphchar] = struct
            # if realleft != leftpos or realright != rightpos:
            #     print (f"Glyph for '{glyphchar}' has different extensions: {leftpos} to {rightpos} vs. {realleft} to {realright}")
        return True

    def _parse(self, filename):
        self.lines = []
        self.top = 0
        self.bottom = 0
        try:
            with open(filename) as f:
                glyphindex = 32
                while self._read_hershey_glyph(f, glyphindex):
                    glyphindex += 1
                self.valid = True
            self._check_extensions()
        except (OSError, RuntimeError, PermissionError, FileNotFoundError):
            self.valid = False

    def _check_extensions(self):
        # Establish font extension in X
        cidx = 0
        for g in self.glyphs:
            struct = self.glyphs[g]
            if cidx == 0:
                self.top = struct["top"]
                self.bottom = struct["bottom"]
            else:
                if self.top > struct["top"]:
                    self.top = struct["top"]
                if self.bottom < struct["bottom"]:
                    self.bottom = struct["bottom"]
            cidx += 1

    def render(
        self,
        path,
        vtext,
        horizontal=True,
        font_size=12.0,
        h_spacing=1.0,
        v_spacing=1.1,
        align="start",
    ):
        """
        From https://emergent.unpythonic.net/software/hershey
        The structure is basically as follows: each character consists of a number 1->4000 (not all used) in column 0:4,
        the number of vertices in columns 5:7, the left hand position in column 8, the right hand position in column 9,
        and finally the vertices in single character pairs.
        All coordinates are given relative to the ascii value of 'R'. If the coordinate value is " R" that indicates a pen up operation.
        E.g. if the data byte is 'R', the data is 0
            if the data byte is 'T', the data is +2
            if the data byte is 'J', the data is -8
        The coordinate system is x-y, with the origin (0,0) in the center of the
        glyph.  X increases to the right and y increases *down*.

        As an example consider the 8th symbol

        '    8 9MWOMOV RUMUV ROQUQ'

        It has 9 coordinate pairs (this includes the left and right position).
        The left position is 'M' - 'R' = -5
        The right position is 'W' - 'R' = 5
        The first coordinate is "OM" = (-3,-5)
        The second coordinate is "OV" = (-3,4)
        Raise the pen " R"
        Move to "UM" = (3,-5)
        Draw to "UV" = (3,4)
        Raise the pen " R"
        Move to "OQ" = (-3,-1)
        Draw to "UQ" = (3,-1)
        Drawing this out on a piece of paper will reveal it represents an 'H'.

        Basic Glyph (symbol) data:
            Mathematical (227-229,232,727-779,732,737-740,1227-1270,2227-2270,
                            1294-1412,2294-2295,2401-2412)
            Daggers (for footnotes, etc.) (1276-1279, 2276-2279)
            Astronomical (1281-1293,2281-2293)
            Astrological (2301-2312)
            Musical (2317-2382)
            Typesetting (ffl,fl,fi sorts of things) (miscellaneous places)
            Miscellaneous (mostly in 741-909, but also elsewhere):
                    - Playing card suits
                    - Meteorology
                    - Graphics (lines, curves)
                    - Electrical
                    - Geometric (shapes)
                    - Cartographic
                    - Naval
                    - Agricultural
                    - Highways
                    - Etc...
        """

        def _do_render(to_render, offsets):
            cidx = 0
            scale = font_size / 21.0
            replacer = []
            for tchar in to_render:
                to_replace = None
                # Yes, I am German :-)
                if tchar == "\n":
                    continue
                if tchar not in self.glyphs:
                    if tchar == "ä":
                        to_replace = (tchar, "ae")
                    elif tchar == "ö":
                        to_replace = (tchar, "ue")
                    elif tchar == "ü":
                        to_replace = (tchar, "ue")
                    elif tchar == "Ä":
                        to_replace = (tchar, "Ae")
                    elif tchar == "Ö":
                        to_replace = (tchar, "Oe")
                    elif tchar == "Ü":
                        to_replace = (tchar, "Ue")
                    elif tchar == "ß":
                        to_replace = (tchar, "ss")
                if to_replace is not None and to_replace not in replacer:
                    replacer.append(to_replace)
            for to_replace in replacer:
                # print (f"Replace all '{to_replace[0]}' with '{to_replace[1]}'")
                to_render = to_render.replace(to_replace[0], to_replace[1])
            # print (f"Top: {self.top}, bottom={self.bottom}")
            lines = to_render.split("\n")
            if offsets is None:
                offsets = [0] * len(lines)
            self._line_information.clear()

            offsety = -1 * self.top  # Negative !
            for text, offs in zip(lines, offsets):
                line_start_x = offs * scale
                line_start_y = offsety * scale
                offsetx = offs
                for tchar in text:
                    if tchar in self.glyphs:
                        # print(f"Char '{tchar}' (ord={ord(tchar)}), offsetx={offsetx}")
                        # if cidx > 0:
                        #     path.new_path()
                        struct = self.glyphs[tchar]
                        nverts = struct["nverts"]
                        vertices = struct["vertices"]
                        offsetx += abs(struct["left"]) * h_spacing
                        # offsetx += abs(struct["realleft"] - 1)
                        idx = 0
                        penup = True
                        lastx = 0
                        lasty = 0
                        while idx < nverts:
                            leftchar = vertices[2 * idx]
                            rightchar = vertices[2 * idx + 1]
                            if leftchar == " " and rightchar == "R":
                                # pen up
                                penup = True
                            else:
                                leftval = scale * (offsetx + self.hershey_val(leftchar))
                                rightval = scale * (
                                    offsety - self.hershey_val(rightchar)
                                )
                                if penup:
                                    if self.active:
                                        path.move(leftval, rightval)
                                    penup = False
                                else:
                                    if self.active:
                                        path.line(lastx, lasty, leftval, rightval)
                                lastx = leftval
                                lasty = rightval
                            idx += 1
                        cidx += 1
                        offsetx += struct["right"] * h_spacing
                        if self.active:
                            path.character_end()
                        # offsetx += struct["realright"] + 1
                    else:
                        # print(f"Char '{tchar}' (ord={ord(tchar)}) not in font...")
                        pass
                # Store start point, nonscaled width plus scaled width and height of line
                self._line_information.append(
                    (
                        line_start_x,
                        line_start_y - 0.5 * scale * (self.top - self.bottom),
                        offsetx,
                        scale * offsetx - line_start_x,
                        scale * (self.top - self.bottom),
                    )
                )
                offsety += v_spacing * (self.top - self.bottom)
            line_lens = [e[2] for e in self._line_information]
            return line_lens

        if vtext is None or vtext == "":
            return
        self.active = False
        line_lengths = _do_render(vtext, None)
        max_len = max(line_lengths)
        offsets = []
        for ll in line_lengths:
            # NB anchor not only defines the alignment of the individual
            # lines to another but as well of the whole block relative
            # to the origin
            if align == "middle":
                offs = -max_len / 2 + (max_len - ll) / 2
            elif align == "end":
                offs = -ll
            else:
                offs = 0
            offsets.append(offs)
        self.active = True
        _do_render(vtext, offsets)


class SimplexFont(JhfFont):
    def __init__(self, filename: str):
        # filename is ignored
        super().__init__(filename="")
        self.font_name = STD_FONT_FILE
        self.font_data()
        self.valid = True

    def font_data(self):
        # This is a represenation of the Hershey Simplex font in JHF format.
        futural = r"""
12345  1JZ
12345  9MWRFRT RRYQZR[SZRY
12345  6JZNFNM RVFVM
12345 12H]SBLb RYBRb RLOZO RKUYU
12345 27H\PBP_ RTBT_ RYIWGTFPFMGKIKKLMMNOOUQWRXSYUYXWZT[P[MZKX
12345 32F^[FI[ RNFPHPJOLMMKMIKIIJGLFNFPGSHVHYG[F RWTUUTWTYV[X[ZZ[X[VYTWT
12345 35E_\O\N[MZMYNXPVUTXRZP[L[JZIYHWHUISJRQNRMSKSIRGPFNGMIMKNNPQUXWZY[[[\Z\Y
12345  8MWRHQGRFSGSIRKQL
12345 11KYVBTDRGPKOPOTPYR]T`Vb
12345 11KYNBPDRGTKUPUTTYR]P`Nb
12345  9JZRLRX RMOWU RWOMU
12345  6E_RIR[ RIR[R
12345  8NVSWRXQWRVSWSYQ[
12345  3E_IR[R
12345  6NVRVQWRXSWRV
12345  3G][BIb
12345 18H\QFNGLJKOKRLWNZQ[S[VZXWYRYOXJVGSFQF
12345  5H\NJPISFS[
12345 15H\LKLJMHNGPFTFVGWHXJXLWNUQK[Y[
12345 16H\MFXFRNUNWOXPYSYUXXVZS[P[MZLYKW
12345  7H\UFKTZT RUFU[
12345 18H\WFMFLOMNPMSMVNXPYSYUXXVZS[P[MZLYKW
12345 24H\XIWGTFRFOGMJLOLTMXOZR[S[VZXXYUYTXQVOSNRNOOMQLT
12345  6H\YFO[ RKFYF
12345 30H\PFMGLILKMMONSOVPXRYTYWXYWZT[P[MZLYKWKTLRNPQOUNWMXKXIWGTFPF
12345 24H\XMWPURRSQSNRLPKMKLLINGQFRFUGWIXMXRWWUZR[P[MZLX
12345 12NVROQPRQSPRO RRVQWRXSWRV
12345 14NVROQPRQSPRO RSWRXQWRVSWSYQ[
12345  4F^ZIJRZ[
12345  6E_IO[O RIU[U
12345  4F^JIZRJ[
12345 21I[LKLJMHNGPFTFVGWHXJXLWNVORQRT RRYQZR[SZRY
12345 56E`WNVLTKQKOLNMMPMSNUPVSVUUVS RQKOMNPNSOUPV RWKVSVUXVZV\T]Q]O\L[JYHWGTFQFNGLHJJILHOHRIUJWLYNZQ[T[WZYYZX RXKWSWUXV
12345  9I[RFJ[ RRFZ[ RMTWT
12345 24G\KFK[ RKFTFWGXHYJYLXNWOTP RKPTPWQXRYTYWXYWZT[K[
12345 19H]ZKYIWGUFQFOGMILKKNKSLVMXOZQ[U[WZYXZV
12345 16G\KFK[ RKFRFUGWIXKYNYSXVWXUZR[K[
12345 12H[LFL[ RLFYF RLPTP RL[Y[
12345  9HZLFL[ RLFYF RLPTP
12345 23H]ZKYIWGUFQFOGMILKKNKSLVMXOZQ[U[WZYXZVZS RUSZS
12345  9G]KFK[ RYFY[ RKPYP
12345  3NVRFR[
12345 11JZVFVVUYTZR[P[NZMYLVLT
12345  9G\KFK[ RYFKT RPOY[
12345  6HYLFL[ RL[X[
12345 12F^JFJ[ RJFR[ RZFR[ RZFZ[
12345  9G]KFK[ RKFY[ RYFY[
12345 22G]PFNGLIKKJNJSKVLXNZP[T[VZXXYVZSZNYKXIVGTFPF
12345 14G\KFK[ RKFTFWGXHYJYMXOWPTQKQ
12345 25G]PFNGLIKKJNJSKVLXNZP[T[VZXXYVZSZNYKXIVGTFPF RSWY]
12345 17G\KFK[ RKFTFWGXHYJYLXNWOTPKP RRPY[
12345 21H\YIWGTFPFMGKIKKLMMNOOUQWRXSYUYXWZT[P[MZKX
12345  6JZRFR[ RKFYF
12345 11G]KFKULXNZQ[S[VZXXYUYF
12345  6I[JFR[ RZFR[
12345 12F^HFM[ RRFM[ RRFW[ R\FW[
12345  6H\KFY[ RYFK[
12345  7I[JFRPR[ RZFRP
12345  9H\YFK[ RKFYF RK[Y[
12345 12KYOBOb RPBPb ROBVB RObVb
12345  3KYKFY^
12345 12KYTBTb RUBUb RNBUB RNbUb
12345  6JZRDJR RRDZR
12345  3I[Ib[b
12345  8NVSKQMQORPSORNQO
12345 18I\XMX[ RXPVNTMQMONMPLSLUMXOZQ[T[VZXX
12345 18H[LFL[ RLPNNPMSMUNWPXSXUWXUZS[P[NZLX
12345 15I[XPVNTMQMONMPLSLUMXOZQ[T[VZXX
12345 18I\XFX[ RXPVNTMQMONMPLSLUMXOZQ[T[VZXX
12345 18I[LSXSXQWOVNTMQMONMPLSLUMXOZQ[T[VZXX
12345  9MYWFUFSGRJR[ ROMVM
12345 23I\XMX]W`VaTbQbOa RXPVNTMQMONMPLSLUMXOZQ[T[VZXX
12345 11I\MFM[ RMQPNRMUMWNXQX[
12345  9NVQFRGSFREQF RRMR[
12345 12MWRFSGTFSERF RSMS^RaPbNb
12345  9IZMFM[ RWMMW RQSX[
12345  3NVRFR[
12345 19CaGMG[ RGQJNLMOMQNRQR[ RRQUNWMZM\N]Q][
12345 11I\MMM[ RMQPNRMUMWNXQX[
12345 18I\QMONMPLSLUMXOZQ[T[VZXXYUYSXPVNTMQM
12345 18H[LMLb RLPNNPMSMUNWPXSXUWXUZS[P[NZLX
12345 18I\XMXb RXPVNTMQMONMPLSLUMXOZQ[T[VZXX
12345  9KXOMO[ ROSPPRNTMWM
12345 18J[XPWNTMQMNNMPNRPSUTWUXWXXWZT[Q[NZMX
12345  9MYRFRWSZU[W[ ROMVM
12345 11I\MMMWNZP[S[UZXW RXMX[
12345  6JZLMR[ RXMR[
12345 12G]JMN[ RRMN[ RRMV[ RZMV[
12345  6J[MMX[ RXMM[
12345 10JZLMR[ RXMR[P_NaLbKb
12345  9J[XMM[ RMMXM RM[X[
12345 40KYTBRCQDPFPHQJRKSMSOQQ RRCQEQGRISJTLTNSPORSTTVTXSZR[Q]Q_Ra RQSSUSWRYQZP\P^Q`RaTb
12345  3NVRBRb
12345 40KYPBRCSDTFTHSJRKQMQOSQ RRCSESGRIQJPLPNQPURQTPVPXQZR[S]S_Ra RSSQUQWRYSZT\T^S`RaPb
12345 24F^IUISJPLONOPPTSVTXTZS[Q RISJQLPNPPQTTVUXUZT[Q[O
12345 35JZJFJ[K[KFLFL[M[MFNFN[O[OFPFP[Q[QFRFR[S[SFTFT[U[UFVFV[W[WFXFX[Y[YFZFZ[        
        """
        lines = futural.split("\n")
        glyphnum = 32
        self.glyphs = dict()
        for line in lines:
            if line.strip() == "":
                continue
            print(f"Line {glyphnum}: '{line}'")
            self._parse_glyph_line(line.strip(), glyphnum)
            glyphnum += 1
        self._check_extensions()
        self.valid = True
