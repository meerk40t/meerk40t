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


class JhfFont:
    """
    This class performs the parsing of the Hershey fonts in jhf (James Hull Format).
    Composing them into specific glyphs which consist of commands in a vector-shape language.
    When .render() is called on some text, vector actions are performed
    on the font which create the vector path.
    """

    def __init__(self, filename):
        self.type = "Hershey"
        self.glyphs = dict()  # Glyph dictionary
        tempstr = os.path.basename(filename)
        fname, fext = os.path.splitext(tempstr)
        self.font_name = fname
        self._parse(filename)

    def __str__(self):
        return f'{self.type}("{self.font_name}", glyphs: {len(self.glyphs)})'

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
                f"Parse Hershey Glyph: format error (nvertchars={nvertchars} not {2*nverts})"
            )
        else:
            # print(f"Glyph, idx={glyphindex}, glyphnum={glyphnum}, left={leftpos}, right={rightpos}, vertices={nverts}")
            # Now we have one line with a full glyph definition
            idx = 0
            realleft = leftpos
            realright = rightpos
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
                    if cidx==0:
                        realleft = leftval
                        realright = leftval
                    else:
                        if leftval < realleft:
                            realleft = leftval
                        if leftval > realright:
                            realright = leftval
                    cidx += 1
                idx += 1

            glyphchar = chr(glyphindex)
            struct = {
                "index": glyphindex,
                "num": glyphnum,
                "left": leftpos,            # what the glyph claims
                "right": rightpos,          # what the glyph claims
                "realleft": realleft,       # the real extension
                "realright": realright,     # the real extension
                "nverts": nverts,
                "vertices": vertchars,
            }
            self.glyphs[glyphchar] = struct
            # if realleft != leftpos or realright != rightpos:
            #     print (f"Glyph for '{glyphchar}' has different extensions: {leftpos} to {rightpos} vs. {realleft} to {realright}")
        return True

    def _parse(self, filename):
        self.lines = []
        with open(filename) as f:
            glyphindex = 32
            while self._read_hershey_glyph(f, glyphindex):
                glyphindex += 1

    def render(self, path, text, horizontal=True, font_size=12.0):
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
            Daggers (for footnotes, etc) (1276-1279, 2276-2279)
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
        offsetx = 0
        offsety = 0
        cidx = 0
        if text is None or text == "":
            return
        scale = font_size / 21.0
        replacer = []
        for tchar in text:
            to_replace = None
            # Yes, I am German :-)
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
            text = text.replace(to_replace[0], to_replace[1])

        for tchar in text:
            tchar = tchar
            if tchar in self.glyphs:
                # print(f"Char '{tchar}' (ord={ord(tchar)}), offsetx={offsetx}")
                # if cidx > 0:
                #     path.new_path()
                struct = self.glyphs[tchar]
                nverts = struct["nverts"]
                vertices = struct["vertices"]
                # offsetx += abs(struct["left"])
                offsetx += abs(struct["realleft"] - 1)
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
                        rightval = scale * (offsety - self.hershey_val(rightchar))
                        if penup:
                            path.move(leftval, rightval)
                            penup = False
                        else:
                            path.line(lastx, lasty, leftval, rightval)
                        lastx = leftval
                        lasty = rightval
                    idx += 1
                cidx += 1
                # offsetx += struct["right"]
                offsetx += struct["realright"] + 1
            else:
                # print(f"Char '{tchar}' (ord={ord(tchar)}) not in font...")
                pass
        return
