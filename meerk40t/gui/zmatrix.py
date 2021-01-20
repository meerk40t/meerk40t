from wx import AffineMatrix2D, Matrix2D, Point2D


class ZMatrix(AffineMatrix2D):
    def __init__(self, matrix=None):
        AffineMatrix2D.__init__(self)
        if matrix is not None:
            self.Set(
                Matrix2D(
                    matrix.value_scale_x(),
                    matrix.value_skew_x(),
                    matrix.value_skew_y(),
                    matrix.value_scale_y(),
                ),
                Point2D(matrix.value_trans_x(), matrix.value_trans_y()),
            )

    def __str__(self):
        m = self.Get()[0]
        p = self.Get()[1]
        return "[%3f, %3f, %3f,\n %3f, %3f, %3f,\n %3f, %3f, %3f]" % (
            m.m_11,
            m.m_12,
            0,
            m.m_21,
            m.m_22,
            0,
            p.x,
            p.y,
            1,
        )

    def Reset(self):
        AffineMatrix2D.__init__(self)

    def PostScale(self, sx, sy=None, ax=0, ay=0):
        self.Invert()
        if sy is None:
            sy = sx
        if ax == 0 and ay == 0:
            self.Scale(1.0 / sx, 1.0 / sy)
        else:
            self.Translate(ax, ay)
            self.Scale(1.0 / sx, 1.0 / sy)
            self.Translate(-ax, -ay)
        self.Invert()

    def PostTranslate(self, px, py):
        self.Invert()
        self.Translate(-px, -py)
        self.Invert()

    def PostRotate(self, radians, rx=0, ry=0):
        self.Invert()
        if rx == 0 and ry == 0:
            self.Rotate(-radians)
        else:
            self.Translate(rx, ry)
            self.Rotate(-radians)
            self.Translate(-rx, -ry)
        self.Invert()

    def PreScale(self, sx, sy=None, ax=0, ay=0):
        if sy is None:
            sy = sx
        if ax == 0 and ay == 0:
            self.Scale(sx, sy)
        else:
            self.Translate(ax, ay)
            self.Scale(sx, sy)
            self.Translate(-ax, -ay)

    def PreTranslate(self, px, py):
        self.Translate(px, py)

    def PreRotate(self, radians, rx=0, ry=0):
        if rx == 0 and ry == 0:
            self.Rotate(radians)
        else:
            self.Translate(rx, ry)
            self.Rotate(radians)
            self.Translate(-rx, -ry)

    def GetScaleX(self):
        return self.Get()[0].m_11

    def GetScaleY(self):
        return self.Get()[0].m_22

    def GetSkewX(self):
        return self.Get()[0].m_12

    def GetSkewY(self):
        return self.Get()[0].m_21

    def GetTranslateX(self):
        return self.Get()[1].x

    def GetTranslateY(self):
        return self.Get()[1].y

    def InverseTransformPoint(self, position):
        self.Invert()
        converted_point = self.TransformPoint(position)
        self.Invert()
        return converted_point
