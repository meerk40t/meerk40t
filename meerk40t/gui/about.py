import datetime
from platform import system

import wx

from ..main import APPLICATION_NAME, APPLICATION_VERSION
from .icons import icon_about, icon_meerk40t
from .mwindow import MWindow
from .wxutils import (
    ScrolledPanel,
    StaticBoxSizer,
    dip_size,
    wxButton,
    wxListCtrl,
    wxStaticText,
    TextCtrl,
)

_ = wx.GetTranslation

HEADER_TEXT = (
    "MeerK40t is a free MIT Licensed open source project\n"
    + "for lasering on K40 Devices.\n\n"
    + "Participation in the project is highly encouraged.\n"
    + "Past participation, and continuing participation is graciously thanked.\n"
    + "This program is mostly the brainchild of Tatarize,\n"
    + "who sincerely hoped his contributions would be but\n"
    + "the barest trickle that becomes a raging river."
)
HEADER_TEXT_2 = "Since early 2024 jpirnay has taken on the role of lead developer\ntrying to fill in some awfully large shoes."

EULOGY_TEXT = (
    "MeerK40t is the result of an incredible piece of work by David Olsen aka Tatarize.\n"
    + "He created this program over 4 years allowing users across the world to get the best out of their K40 equipment (and additional lasertypes).\n\n"
    + "Despite having no risk factors for getting cancer, he developed a tumor on his tongue that metastasized into his lungs before the doctors could stop it and passed away on July 26, 2024.\n"
    + "He was a mentor, an inspiration and a friend - David you will be missed but you won't be forgotten.\n\n"
    + "Please join the fight against cancer and consider donating to one of the many research and charity organisations across the world.\n\n"
    + "If you are interested to read more about MeerK40t's development history then please refer to:\nhttps://github.com/meerk40t/meerk40t/wiki/History:-Major-Version-History,-Changes,-and-Reasons"
)

class AboutPanel(wx.Panel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        self.bitmap_button_1 = wx.BitmapButton(
            self, wx.ID_ANY, icon_meerk40t.GetBitmap(resize=150)
        )
        # self.bitmap_button_1.SetBackgroundColour(wx.WHITE)

        self.__set_properties()
        self.__do_layout()

        name = self.context.kernel.name
        version = self.context.kernel.version

        msg = f"v{version}"
        self.meerk40t_about_version_text.SetLabelText(msg)

    def __set_properties(self):
        self.bitmap_button_1.SetSize(self.bitmap_button_1.GetBestSize())
        self.meerk40t_about_version_text = wxStaticText(self, wx.ID_ANY, "MeerK40t")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: About.__do_layout
        vsizer_main = wx.BoxSizer(wx.VERTICAL)
        hsizer_pic_info = wx.BoxSizer(wx.HORIZONTAL)
        vsizer_pic_iver = wx.BoxSizer(wx.VERTICAL)
        vsizer_pic_iver.Add(self.bitmap_button_1, 0, 0, 0)
        fontsize = 16 if system() == "Darwin" else 10
        self.meerk40t_about_version_text.SetFont(
            wx.Font(
                fontsize,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        vsizer_pic_iver.Add(self.meerk40t_about_version_text, 0, 0, 0)
        hsizer_pic_info.Add(vsizer_pic_iver, 0, wx.EXPAND, 0)
        hsizer_pic_info.AddSpacer(5)
        self.meerk40t_about_text_header = wxStaticText(
            self,
            wx.ID_ANY,
            _(HEADER_TEXT) + "\n" + _(HEADER_TEXT_2),
        )

        self.meerk40t_about_text_header.SetFont(
            wx.Font(
                fontsize,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        hsizer_pic_info.Add(self.meerk40t_about_text_header, 1, wx.EXPAND, 0)
        vsizer_main.Add(hsizer_pic_info, 1, wx.EXPAND, 0)
        # Simplify addition of future developers without need to translate every single time
        # Ordered by the amount of commits (as of Jan 2024)
        # tatarize ~ 11.800
        # jpirnay ~ 3.200
        # Sophist-UK ~ 500
        # tiger12506 ~ 90
        # joerlane ~ 50
        # jaredly ~ 15
        # frogmaster ~ 10
        hall_of_fame = [
            "Sophist-UK",
            "tiger12506",
            "jaredly",
            "frogmaster",
            "inspectionsbybob",
            "jondale",
        ]
        meerk40t_about_text = wxStaticText(
            self,
            wx.ID_ANY,
            _("Thanks go out to...\n")
            + _("* Li Huiyu for their controller.\n")
            + _("* Scorch for lighting our path.\n")
            + _(
                "* Alois Zingl for his brilliant Bresenham curve plotting algorithms.\n"
            )
            + "\n"
            + _(
                "* @joerlane for his hardware investigation wizardry into how the M2-Nano works.\n"
            )
            + _("* All the MeerKittens, {developer}. \n").format(
                developer=", ".join(hall_of_fame)
            )
            + _(
                "* Beta testers and anyone who reported issues that helped us improve things.\n"
            )
            + _(
                "* Translators who helped internationalise MeerK40t for worldwide use.\n"
            )
            + _(
                "* Users who have added to or edited the Wiki documentation to help other users.\n"
            )
            + "\n"
            + _(
                "* Icons8 (https://icons8.com/) for their great icons used throughout the project.\n"
            )
            + _(
                "* The countless developers who created other software that we use internally.\n"
            )
            + _("* Regebro for his svg.path module which inspired svgelements.\n")
            + _("* The SVG Working Group.\n")
            + _("* Hackers and tinkerers."),
        )
        meerk40t_about_text.SetFont(
            wx.Font(
                fontsize,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        vsizer_main.AddSpacer(5)
        vsizer_main.Add(meerk40t_about_text, 4, wx.EXPAND, 0)
        if self.context.root.faulty_bitmap_scaling:
            info = wxStaticText(self, wx.ID_ANY,
                _(
                    "Your system is using a very high userscale value: {scale}% ! " +
                    "Unfortunately there is a bug in wxPython (the framework we are using) " +
                    "that will cause unwanted upscaling of images in this configuration. You will recognize this by looking at very pixely icons.\n" +
                    "As there is only so much we can do about it, we recommend lowering your userscale value to something below 150%."
                ).format(scale=self.context.root.user_scale)
            )
            info.SetBackgroundColour(wx.YELLOW)
            info.SetForegroundColour(wx.RED)
            vsizer_main.Add(info, 1, wx.EXPAND, 0)
        self.SetSizer(vsizer_main)
        self.Layout()
        # end wxGlade

class DavidPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)

        from wx.lib.embeddedimage import PyEmbeddedImage

        david_olsen = PyEmbeddedImage(
            b'iVBORw0KGgoAAAANSUhEUgAAAMgAAADICAIAAAAiOjnJAAAgAElEQVR4nDy76a6mR5LfF5F7'
            b'Ptu7nnPq1Mpqskk1ZzRjS7LGtiDA9jX4iy/D33wXvgtfhD2QAHsgDGBbwKhnutkLySKr6qzv'
            b'9qy5Z/oDbX+LAAJIBDKR/4hfIPB//l/++3EcM6BzjgnVNM393fOHDx+G47Db7V7fvPny/a9I'
            b'oR9++PH4+PR8HphuU6H7tr3ebd/e3GrB7WVUUhJCnPeFim6/3b94SbW8TPPlfL7ZbPrDaZwG'
            b'KWUOkVLadatpmoCQ3/7uHz789Mfn8+dmzdo1b1fsX//rf7VrN9Gn3/6n33XdmhL+93//f+YE'
            b'r169IShSSpzzqqoQMYRAKNSyyTMwZM2q4YL0w2CtnRb39Nw/PZ6RSEBd1+1qveWcU0Eb3dDM'
            b'sCBjzHtvjGua5vbl667rSkFCSEjZWgsAUkpCWEieamHdJBnddg0rfu6PNMe2IqtWSVkEJ7lY'
            b'G6aQLCFIBBGUpZSMC9a7kglXkktBCPnww4/e25IS56TVVV1rrQSj4vh4iKFQXi/GPx8uqmnf'
            b'vXtXtRUVOefABK0bDYQsy7IstgSnit1tO63r0cyX8zgs5jwu58F8/PSYQPW9j0W03U3KdJwc'
            b'I266/LBq5b59/e7d+998/U7K8vmnH+4//mx6rwUgLk3tXr9prq/a5GGZnZsiQbnM4XxaloVq'
            b'ta6rDaOyaTdCMN0IyvI0nx+fPj4f7gZzWWAJEBRV17vr1y/frNqNGZbj8cwIIZRSzNl7v8w2'
            b'pUIpffXi5abZLIu/v3+gyLerrVKNrl16vpAEJSfv/TiOF13z9apZdbfXN6WUjIBcdZv1zas3'
            b'1ap9Op0/fvxIU3r1+qW125xjVzc3NzfzbP7u7/7u493neZwYY5vN5uq23e5qpuI8m7XejsPy'
            b'+HB8fuqbphW84pW0JpaSSykANMaSUpznGbHkCv1gJJPI41atr64307ScLp8Oh0POlABdbdZX'
            b'+1sutHPOLN5O/bppo09KqaZtt9u9VFVK6dOnuxjj/vqGMTYMUyllf6U4paOJteQAUEoJIaTk'
            b'QkiIGZFXWhOaECMC5UwKwbhkTHJSMMaYiwmxuBD85NJoUkqrbvd8eLTGIEqzuHEcBaNN05zP'
            b'Z0rEdt/drm+bdlOQEkLGcUSSmq4SnMeQc47JJ2/8eDntWm1sCnE5nYfHw/O0mHHx8+J2u50P'
            b'DLL1gUgKEUpX67Zu962Pflmv17/5+puvv357ePzZLbNdTF3VghRCshJYq/r2+qWWbX+Zn5/O'
            b'QjY5kG5jh0uIgZZMfYou2Lpb72+um1aeL9rGKYKrcn2xQ78MOaJLOE5umU/jZRqGkR2en1Sl'
            b'67p+Ohw//vxZqUrJmlLeNGutICx+Gm2056vd9ZdfXVNeAWUhRkkZ5mSMGQWjbccrRSklnAFy'
            b'zjljTEulheSESiEY4vPxaZ7HblW9/+pdSeXh8dPv/vA7KTnnDJiudLPZbKSmyzj9x5/+yRn3'
            b'/DRUVdPW+qsv/4JRcXf3cPf5MaWklKlrF0IYhoExstv4XauliikvLhCuVgAppkAIWa+2xoBg'
            b'reTrEEqOpOJtKalr1wBZKYWM2sUM8xkRQ4ht2z49HxGxqpq2bQuhwzgvZnl4uqOs7FZdwxkn'
            b'yJCU6K21wdecFya4EAyoTMmH5M3o67pFYIwSzrCk6GJw3jqXFBeMakp9ybQQAoV6n4dhapoq'
            b'Z9BartedVNVivY9xmIZcPGJxxg7jJcWitY4x2Sn9fHlebGqaZrY5JlZASMkIVSWzEpNilJac'
            b'g4kmEcoktryuphg5ElJg7i9Pn++fH+7H82lJUyXp9XW9bXetrrXsANTcH10ElIxLzStO7BSi'
            b'tz54lyZrLDiimYny0h9Hs8i6udm/rpaZHp7Pp2F29NPzHN3oFpdiZOfD8dXbN7vt9nzuP8OD'
            b'NYGSxFldMnnz+p2WerzMU2/2+5fffPPN+/ffnIajcy5Yd3x6XMZh/NzfEzovy7fffltyjsHm'
            b'aZwWJ7Xqx/n59PSnP/2RUVyW6eZqQ9j7ApFQ/vbty6vrFWPs1D8F487HvkBqO3l/f//hTz8J'
            b'qgmhm3XDWbPurhhTTw/jNDpjHOKitck5W2u1lpUI1c1uv20IJ4SQnKP3nlJ6dXUdvez7aVn8'
            b'PHnnE2Niu7niHEMyiBCBlJBnFwCga9frjUqAS98TpKpqhKqHabxchhhdzplmyDnnnAljQqiE'
            b'qWTo+4kxlIpUteCCpMKctYsLOcaMmCLDUjFRkKaUefBwPAyUqVpjykHpartepegvl4PxUykl'
            b'lSilULrtCuYMq7n9+PGn6KI3duqn6GJQLsbc9+PpcvSB3NxwREZoxRkjmCjE46k3xiWXsZDk'
            b'FjssGZC4qmoopCyQz8N45/rz4ZkBNEqZ3jHBXl69+PbrN21XoLD5afzhT5+ejeHVhRG5mGgm'
            b'XzJhtGJCzMb0d8Pd00fKyjT31k03N9fNbqfqdR1wsng5Xcw4p5AFFZxztmpXUz+f2IVTtV3v'
            b'x2khwNt6tV7tr69ut+ureBPvPj+mQkOiL168rmo9juf+cnmGch760+nknDsN/Ye7O0TkXNa6'
            b'kqJCxJyhYL6/v+cCnZsJDR9++iOgb6r6crm8/9Xbvu8ZxRjz4fH09PSkK/H09MSB50SbboVR'
            b'PHx67o+LkvXpuSdZQEy5lEwJpVxzLqnMiZ5PU61ku26lkExIIaKSumT8dDgvs+U8pFQACGOC'
            b'UkoIicD64YKzW6/Xm92NlDKmMs6ztW6z2Va6Mc4ezvc5Z0IYZbDZtt4t1vqnp6PiVJDCEYCB'
            b'i8Q6Ny1pnExVKyYpouZcX/pQgABAIZQxBjlCTjnaZV44pxSRUClEpesOcymlHA+WctRaK6UI'
            b'VYQJRMoYs4vhAjnFq83GW9ef+7vDw+npEIFNc5KDRyxuWaxbvLfe+5JyMgsnrKobrPm2VaQQ'
            b'wtilP4UIJWVJGSmWEWgqxUvRREnKKq4VVXFZ/Hk4P09mhn5Jbh6Cjf0451Aq3ez3XFa1ZGU8'
            b'9MPpknJYltEHu1hrSq6uXyREXjVlMFOaSy6FAxGM/o//0//w/Hg8Pl9ShOjzMvvoc9Os3739'
            b'1Xq9r3RNiLj7dP9//d//8eH+AZBwUuZ5GIbh+fn51J+NswWh3axUVSEldd1sNxuttPfBmSWE'
            b'ICuhKnG+nA7H+2E8WzMBJAC4eXE9DuPhcByH4XzpvfOMC8VUXXVa6fVqy7k8Hs+PD0+Hw/l8'
            b'6hEpIqGUCa44E5QwKBh8cMsyL9YY73wpmYZEvAMfIEQkKJRqdaWFlHVdNa0mjCChs7Epga5q'
            b'XdWMi5Rgdk6qhlAeMxjrjYu5oNT1arXq+7NzzoeYUyFIKRdCCMYkZTIBSUCByIw0JrK4vJi0'
            b'mOw9hACAnDPJhCoFc8acijFL9KmqKiW1tcE7TxnRlZBKSFG7EIfZIDDORQieceQUtOLrrmkq'
            b'lbz185xTYrxiXJaQnTHW2BR9iaGkyCkyirvt6u3rV19+8eYvv/36r//q269//SWj3Pu0XV39'
            b'+stfVRUfhye3jBQgmEgBBSXeLZfj0UwOSyWqNegamFqMH4ZpnBcbfEo5pBBSmM2UIalKSa0L'
            b'gLXmMs625ERQN5VQshCMKSAjVAhW8XXXXEd/mmeTA9uurglSyXVwOcdy9/n++fn4/Ycff/jw'
            b'4f7+fhwv79/eejcv1jwfDsO0xAK6qpvt7u27X5WcOaGVVJjQzsv5eHw4PheOROL59FxpxjlG'
            b'CC7MUvMY/Tj2iCWlEmNumrarNpvN5nI+EEKEFohU1SKWaE2gEjmjiioAkmKOOQJAjDn5wJv6'
            b'8BiXaRn6cmmibmoosuS03111DcRMCU26ItWKURmR8MPDkAuvmoqJajbJBK9VfXXVUcrO5/Ni'
            b'jZSyXdU5Z8oEcml8EVxXlZScScG55IxTwshkFiSSM00QXSHR+nl21tpaKMiIpBQCWnFKpZAg'
            b'Yw4hxpwQoqo6Qvk8jzE4yaFuSQjlfJl8HBmttF4JKWMMi7kEb5xxfkYsCeO060Ql95cFfMbo'
            b'bc6OYSEUC2EBE+OEN/L29vr165e79WZ/fQ11C7MDQlW1ut6++uL923l+PjzV/YUss02QXr14'
            b'efPiWrIEhSqhBWlJohPTgU3Oo/O55LNz7nQ5DlPPCAXIVVXVdc0JVVwMw7BEezg/LsXI6vX+'
            b'Zo0sLea8LCNThf37f/f3QghC6tPh4Fz46quv2m7tvZ/6Sanh97///fd//kFr/e6LV3ZePn3+'
            b'sAzPpOSM5HA+DPOSMCckPqbjcMECkjJE3K03dfUKSjLRns3Qj2M/9W13pSq1LNPT80NK6fj8'
            b'w/c//NkYnxMgUMF1TjRnUErkEkO0KSUh6U6uvI+EsJxAyirFMgyTMQaRckIwM8ZbzChlRSgf'
            b'pxCLF0KHCFJw3aiYAAir2kooGoLzyQld8VptupXQahjGvh+H0THBta6rdq0aHMYxh1zVNSH0'
            b'PEy623OGiDiZ5TxMHKGulJaMIimQEBPjhDFApKnUwGRGmiGUVMCDCVBo8qF4nwuQVbeVimnF'
            b'EEHm7L0/XcZ2fSOoRBCxRECWgU3GHg7PwU85mBwmG02JAZInECVnL7braQljXowxpaQc0uKM'
            b'MfPL17dNo3abtql4Qj+bS5n7h8fD09PCubi9vcF1R+0zUrB2/unjTzeb12/evv3m6y8hmegG'
            b'Z8PpyT0cL30JLiVG+KrdMmDTPFi7xBhHNwkhlBDJR8KRMd7WKw76Y//gsl91zX63kYpab4bp'
            b'wgSyT5/Pv7TT0+RyjsscXt6usIEY4/VuL//5X/7Tf/qHdVfXjbY1PT6aGGMllXEBgBDKQ3T9'
            b'MP3uu99fHQ+U0lbrq802Rb9fbaQWlKKQTIJMKR0Oh6YWXatTcN7F58fz6XT6/OnJu1iAnk+9'
            b'jxkZEDIzXvppjDE2Tdc0bQUCgGhdV7p9fHyebXp3+1KrehzHHGkr9rXuYrKH05NzNhZQimag'
            b'hCnGVd21uYCuGqHE6XC0Me92t1TUOabD8eJcYFwzJlLOSLgPWQihm8ZMxrhY11I3GySZEGKt'
            b'NTkSLmRVUU7n4EvOlDIpORHcleK9BQBJ0WWbUowhmACpTMJS75dlHgjNtZIFSMqE0iJ1VQoS'
            b'zgC1VionzJCrukPCn57PD48Pfjlf7eu208XHHGIla0lITvRyihKJyHj0YVkmwFwLqmX14mb7'
            b'6s1rpdSn+5/7cRBCxZT6fg5BfvXlX67WLRAkFAokWcl/9u03tdgSzoBR6NZszCYMJsTny+Xz'
            b'5WJLUoIJwZuqqpTw3o7jGJVOKUWfHu4eEfH29nbdrD8e7wVVizH3nx6Cjc45M1tEWgqySm1i'
            b'8saYnAghytl0PveMka5r60q1ze1/+9/927/927+9vb1ZzHy+PL/86p931cqnyJViY9/PY8wp'
            b'A/l8f79ZrUqK3trL6VDrikHhNVvuFmSotS7FPz8/9wMjhbTNpmvXKX4chiFlVLICyhCpEAKZ'
            b'y8VQlqquur2+ElrZyS/Or9Za1zVloBu9btdcasrgdBybVfXw+a4fzlxSrSVQRjnfrq9KFnf3'
            b'R6XJ/uqakGacnIusbVe58OQzItFVJ1XOuRBCkHLrPaUIBCiVquKEUiTMBm+cq2tNRatqGr13'
            b'QCnVSnUEwXvvS4IkOKdM1SmHkALjFAqSQpEkn9EbH0OMCSqljXc2+KpWm02nFAdkzodxitY5'
            b'QMGoyIUNSzwdTnf3T0LExvOuq+pVK4lWDCEGu4RVw7zNDJhgTYZaKKmaWla6WXUvXr0GxH4Z'
            b'nk4OBXvzxZu/2lw7A117w1oJGGWjvv76qy9/9aqSVfI82BRi4MZf+suHn36++/l8GXzJEXNh'
            b'BQWhEKmNgSSUXHGavffOuWlcvPEQyWq1cSY2zSpZYobwYI+UUsE1ZTJFYLura2utdY8+ZMHR'
            b'Wp98uN7dxBSSD5fp/Pvf/eM0Xj4mo7V8+/aNktV+f005p0Iuzl+GgVHW6KrbvNhsNpDjcDnf'
            b'Pd2fjoeSwnazz0AVEYqrlMEYb4wxGxdj0nWjqrppV0A4pdR6B6QQXq5f7EOagovdavXm1WvC'
            b'6OP983I0yGC1qTebVX2ZlFCr9VYI9nw6jebgUi8ruHm5b9t2MT5mFgGrqot5IKSR6jpnFgND'
            b'YDEpIMQFi4hCq4JofSilCIEhpBABCVOKEcqQURfjOCyzMz5kKTQSkgqLPmeIPiNDgiiFYlwp'
            b'SjGEEJzLKTNaMjBkIDkrJTifoFCmGuOcYJxSmjJOs/chA1BZr0/PR4DABFmvOmRtCHG2xSfm'
            b'ZnMeFyUK1IRXjDAKkBG9FqgIW7VbWWkmeKGEKa3rCjcbEBKsefHiha6rqulubm5YtwUTwVNw'
            b'E/gFILWbNcg16BVkrU8j2CmHeQnmMveLn5EzQUg0LgaMlHjrrLWMoBY6ZygRjfd2CpdxdCFP'
            b'i0tI0hJQSkZpiQQpq3TrvJ/nmem6ZpIty5SS44wSAjnnqqoeHu8/fvzp6fnh/tNnTmhwPkXf'
            b'6fVQRsUuGcnxcDKLE1QQyYWQWujNqq1rzX/1JnjzT//02w8/fG+iFbTyLjIq9vut4DBPwzgs'
            b'//jbPypZX4alattf2HeaUsx+NnO3vuGiDSExxmStpZTjNPNpPPbHzf5qveqUTwhE6qpqOySk'
            b'anS3bhljhBAAaERLSE1IPQ1O6na1uQZQyxK4XCOJ4zSoKvkQYs7UBUSMMZdSnEuMc4AUQgRw'
            b'qSAieu+HaUbChn4hxEopOaelFOdmAFh3K6VUQTYbvyyzc44QohhizqSg4poKkZPL1kMpjPHg'
            b'EzLBlQCMxhcXM6GAhcbCo0+KEGR1Idp7U0hdtzcxipjS6WKWOfpGpFWtOCEodMVLAqmVWq1A'
            b'SPAeCAUpoa5hmUsIu836+tUr0AoQIUeAADHkEAmTIAEKgrUwH8AxUC20LVlC1ajtfpUicQ6m'
            b'yUzTMLvZO2ms995LqRSyGLPz4EJBKnXVEcqMjT6XwV7W+6vNrqOCIiUFgDEiJNC/+W++DdGG'
            b'5OpK7vcbxmnwNnh3++LGLGZZlv3V1T/8w2+1VMu0LIslWZwv408ffr67v08xV1WlpCKEhOBX'
            b'm+71m9uvf/PNu/dvC8su2m7dSVZFG0pOb9+++eLdeyX1+dj//nd/OJ7HeV4o4U3btKumXXe6'
            b'VsjyZtt1645xMRsTUyZUxATOp36YcyaAPBfiXBrG5XwerAl13W62m81uK7SiXApVAQrj0jCH'
            b'mEVdb12AYTRcaMqUDz5jLgApZWOs94EQBkhiTACYM2RAH+I8G+d8jMk7zxjPKaWYEAARoBQA'
            b'BMDNepVS6vvL58+f7+8f5nmmlEopAHLOQIigjPvgx3lerIspMSFzhJhKKShExYWyvkyToYRl'
            b'oEq1q/WesfqX+Qwi2e2vuODRJ2NcCoUgZygJcq3qVKAgZYRBLj5EQCSMgQtgHRYgnAMUsBZC'
            b'AALpeDDjsPQGQ2IlQAxhnpZh7s+LLEiSK35JyYzjue9HH3yI4dKf52VK8RftCyFmF2Ax3roY'
            b'QiZCrne7pltlAB9jQkooByypJBdDSJFxVnUV/cu/eXU6H8bpRCjUVUUJBruM46CkDCFc7a+V'
            b'UtM4HQ6nZba1bmOinPKUilmWGBOjrK6rrmurRrdtrWqFDI798fPD5wjxxYuXu/ZqOI/H40FK'
            b'1dS1lFrLhhKRC0kRXAhIcb3b7K93VSMA02rTtV2bEzkczv0wOZ+M8cY4RvUviQlROZd+/vnz'
            b'6TQ1zQoLC6EgoW23abtNzPRymc4XUzfbxcScyWL9NM8+xZgDFyyXxBgtpVhrvY85Zx/isiwA'
            b'JKWUS/HeL4tJKf3S00TnCAAjNOXgnS85CS60kjHGceovx9M8jZTQtq5rrQnBXHLOmAuElKzx'
            b'8zQtszPGeBdjzjlBzOhDsj6FUGIsCFgAtW7bbgdULS4EnwjjgvOSIXrvrXfWRw/eZWuisdb6'
            b'AIRRLguQEJL10btgp9k6jwQYY5Cym2Y7jGkcluE8ni7DYRyHIToDyUPOkEDSapnN4/3nfng2'
            b'y+nT3cfHxycEQEatNTlnQklOGGJyAaZ5QeRIRSyAlLTdWtVVzCWWRAVLEHwKQEqhuWAEWphA'
            b'+s2/2i1LX0okpDi7eLeUnEP0//jbfzyfzy9evIBMv3z/1YcPH/vLCIUS5G23rqsGETnjTdNs'
            b't9vdfoMMY/KLn59Ojx9+/vHp/NSu67dv3vEoDvfPD3f34zD050vJ8PbNF1999U3TrXMu4zjl'
            b'UqpGNa2WinIltru9EHoxvh+mxfjF+MW6EEvbbZRuS2HOFR9gHJ0Puak2++1rs5RxdD5CytTa'
            b'5H1GKr3Pp1N/GcbLePHRhWScn7kk1pgYY85QCqSUnHPWOe99ziXGmAvGmJwLpUApEKwN3iPk'
            b'nJIzcwqBMSI4h5IOz0/OmJKzEKxt2rpSCMVZ51zwIfkYUsiQC2WMM0EptdYzLgRXNsRpMLNx'
            b'AFQIiZBSSICCMB0LWWzwLuaC4zTHEFLKwYWwRG+iM2VZ7OF4CDlxqbmqgDAf8zhOl3M/z8s8'
            b'zsF5BsCReLOcD4fDw53mmH2CgAiEQiGl5BCyByXqFNLT46e7uw+Xy8M890qIN+/e6VozwRgT'
            b'QGkIKRaaErpYdtcv2tUqltJPk4/R5+SSLyTH4ogoqmZcE+QBWCKqcIn0N3+9V4ze7jZrxZbj'
            b'83I+lGCStdGF77//MRa8url9Ol6sjyHmeZ4Joblkay0gXt++ePvuTbvuCEVAjMkDgVLyOA7B'
            b'x0rXNa/HQ398PJxOp3meHp6eF7u8fvXy9vbm11+9hxJ8mHVFN9t6vamvbrav37385b7nefE+'
            b'QqExlpKIkq2S7e2Ld1jU4TDmRLVqKJW5CEa7VCRlmvMaqI6JGJuXOf7w46fj8XI+D/25pwSk'
            b'EhAjgXI5n51xBEBLyShLMRYoSkmzLDlFAgg55+ghlxyDm6dKcizZmdlbwym0TUWx2GV2ZuEM'
            b'pWBQcvIuOBuccc4txrrgU0xQitLVerVuu07XbVVVjAkfkg+xIBVSUSpSzl3deJ8WG0Is1oVp'
            b'nhcze29jtIQAo5BLCtGnmDJiJjgsMwpJeBOBu8SMz8bEyfh+mIwx1rsYnDXTMp2X+RKcwZRK'
            b'LIxKTilAMmY8nw5Pjw9aqqZS43T6+ec/TvNp1TZffvnVX/7zvxJcM6EQqA9xmW1ICQkHxDdv'
            b'32y2W2/d/cN9PwzBuRATpVggdF3dtnXBaL1Fllebdrtf07/4Zr1V1aumauKClye2nCuMFaXX'
            b'ty+pqr//9PiHD5+O48R0tdvvCKchOsIAOZG17na7/e3t9nqv23qz21aNHof+px8/0EL/5V/9'
            b'y7/48i95Yj/84U+fPv2EpGTI1oZhXA6Hu9VKti3rWlyvqJBBqSwkyIo1tdpfrxc79kMfUzKz'
            b'Q+D73cuSWFNdIeh5CmZOObOUEJE39f54CEJsuu6G8aa/uLu78/F5sbb88fc/9Jd56ufggjPO'
            b'zoYWREDBWMrJmMWaBXLhjDLEEiOBIhBpSQyypEhyytYkb0oyJRlGEqeFE8zJB2eCM5yiZIwT'
            b'QkouKZYUc4wxekIRAAokJAQBgVDGBJcqJchIckbCRNu0Vd0AEGs9ZERgMRazGMRSN6qqGKCL'
            b'cTb2Yl2fi3dxWfxIFGm2HUgViUTZRqx7U1wSSyAPj+fn83kwE+NAWTbmzGhYrSsluWRVCBBS'
            b'UBVbdarSAiABBO9HQCt4ysk4O1dKvri+auouZf7p88EYp6u6lGyspRS1Ftt1RxAoAYqFE6qF'
            b'FIS6xVDCJBdKaSGUEEzV1Wa/2V3vWc20JmQt+NXu+ouOJe9ks8JqTbrbd4P7cvAR+fHS9/15'
            b'1TXXV6vH+ztj7GJjQfQhjPOEgknFXr+83V99e3h6Y60d+6HV3be//gtW8Onjp4fPPy/LQild'
            b'bRqzzI9P5//wH/53SNPti21bMdvwp9Px8fB5NVwxQQknuSRKsWkaRmu3JIJCKy54LXjLKUIx'
            b'IUYoBJFYl2S9AlpNczTGzLPxngVPrLUEpXcuhyhrKQjPPtnFKeG7qybmnFLJOefgU06MMSGF'
            b'zQkAKBQKhUChBCmjHEUsFnJKiVBKCSUMSMnFR4+JgCCKySKY92itNWYx1lKlVNNsVtvVaiWl'
            b'zDGdLr21y9Vuz2WlZJWyQ8hIaauqVdv5ZeaMiCpbawByTFZQqrWMibiQFrNQjIiJ11W9WXX7'
            b'rXNhGpen8+AfzzGQVdvVUrjClwDBLkrAbltXVVtp3jQ1ZNR852wMIeScfQwhBMLoarO+nE+E'
            b'lu1qA/gFIWSahvu7Z+Po4zE8PJzN4pjglPJV087WxZgeHj8pVRFkba204CmlaZjnmLjkweXh'
            b'vCQeC8uVqAjjlDL2q6/e02JlpTaburtuBUcuKkek5SuxprdEA9e//+6Pvz18TkvUevf29ZvT'
            b'eTiexxjTsiwPDw/jMjdNdXt703Wrddfc3d396Q/fDcPw6e6Olvzdd9+dz2dE3Gw2dduVHIJf'
            b'tl01jwt/9aKq5WwsJdOyHEM6b6/HerXmQkpVKdnudvXUeyyaoGRUMy6FSpQJHwoiApLgk5Ak'
            b'RHeepvP5nEPknKcUjJl/85tvnp6e7LJorRmhxpgYvXPG2UAp5YSmAjGGkjMByimtZFVKAQBE'
            b'JIAAhCIrhTqfAWPJSJFyKjgVMUbM2LQtpSz64GOIMUIplVRSyv2Lm2a11kpN0/TzTx+8dev1'
            b'erfb5hCRUsoZEhG9c8557ykClEQJpYSX4GYzLcFIxbgoQDhSQYnMKecEkLFkhki7lng3Dv3Q'
            b'X5aSmSCF5CqEYE0YzhOW0NR1aHVZCa2rWtdAalkTHuM8z+fxOM8zp0xrzfVmssUnG7IkvJvt'
            b'OJm+n2jMLcUmxbQYx4WQorG+xOLMvNjFIFJKKeecEBA8aUl8DKWk5EvEQBVFScfBEDqwv/rP'
            b'/zosfYOuVWWj2apWueBxdg/P90NgkWpRr9D2xM8A1o+kWu13221dt9O0DNNslsk7M1zo6fD4'
            b'4/d/uL7ZXU7nw+H04w//69/+b/8ue1fMon6c7E0AACAASURBVITcrze6qjmXALnEmmDsL8Ph'
            b'+cJ7NM7c3Lxc71/YEJVspKgIyYRYALbdXLc1mSe/TMm5wGhCoELo4IEQAoSmiM654N04jsuy'
            b'lJhijFhACJFSopT+wreEEP+/MfS90rrSmjOGADkBAEDOUkoAgEIQf6EKJedcCiUUEAELAEFO'
            b'GaUEShGMa6ViSs7axZhSSl3XTdNwKRgX4+V8cK4UrLhsVQUA58P5fD5KxZum6rq2qSXjMoTg'
            b'vU3BASmEkJBiiDFEN0yhQKg0pwTbdkOgtmbKyZVMSwKpi6AB88xJrOpqu+mUUJ5TO/WG6+Dg'
            b'cvFQRFVpyvdMNtOweG/neT6fz8P5knJsm44qsbt5+fNPH56fHxAxpZSw4ZRytbvZvAuJfPjw'
            b'4aeff3bOF1JiAKSs4jJGX0qhDCjGGGPKtkAwDqlUhFIkGGIcR2Pz49PzgT0eHjrFaS18Xi6T'
            b'IRCQMrPMz4+fT1M8DtZneHh46E+n5uaKJVm8uX35rmm7vh8fnp/6YZimqR8vlHRPD48pOm9N'
            b'SXk4D8bMJfh/8Rffvnv9qlnvjPdDP83LOE72+Hh3vdtcjhfGCRX07bvX6/3V4/H8cHrqL2ay'
            b'5qefHwSv6/pms75FkqbpOIxjCJxRKWQdI0UkpZQUorPB2pBDlIzbmKZpYoRqrbXWjDFvbQhB'
            b'MK61ppTmnMdxLgkgASFEMomMEkIoIQQoIYRRTgghiDnnUkopOSbKGGFIQk6YS4ZCKUFB7bwA'
            b'JRRQCgGQKYEYXMohzaPxLsbImEClAsAy23melRbRQ/Qpx5wywUwAOaEJUP4iy4QzVVfgYLws'
            b'03yeRlCSrNtq1erteksx15WQlJQ4crSCeVLRV7fXb16/0bpNIWoluqaCkrfb7vb65v3793Xb'
            b'LePl02N/ODzd39/3fU8KdF1H5UYF+tPd6U8/PNzf33POhRA557aWuijGV5Rzzo8+kMnMQBKl'
            b'KCq9WTdCMKUkFxi8PR6f5+UcomV8req1qEQAZ6NxwS4XE3Ng//7/+Ltfvb399ouXHY9ghmHE'
            b'Wikb86rVyFLI5XwZi18Uxk6yVlDdqNt9u7/ez5t607DDWf38KYyX5zDmwHE8luPxePh8H41j'
            b'gMZHhnD74np/dft0Oh+fnk/PB8hZMFmrmhHR6Kpum67ebtbXuah+st/9/k9P5+P3f/65a/eV'
            b'3slfb5VcVVU4HdxiQ6N0XXUUqxBCCAEAUgjBuhjjL9jJW5colVzM8ywYyznP4zSkpJSilCYf'
            b'9vtrQlhJOUBghDMGjFLGGBYkSBmlnHNERKAAQCA7xzinlBAfXfQhQyKInLIQAgEASrBAKQlj'
            b'9t7EnAgnWkmqtHOuP5xyzlrXN1dXWkughHOeUunPfYYshJCKMq5S9rkkTrkQghHwy2QXEu1y'
            b'GY3tj3HXvthvdS1JzuPQK3ZRPL+83lZ68/7d1y9u3iDKELOU/KFrjJk3q/XLV6/q/Ut76X/3'
            b'3c//9N1vHx/vn56eUkpds9p4GB2ox9Pz87MxlgJBoWMAa4OLLpPJ2I8I8jwuPuG4uAShqhRD'
            b'7HbXTavaRiPEeR5jDtMyTREK36p2J7Vw0VA/0iyWMCdfWL8sD4fj9a5Zvdx1ra55abQihL1A'
            b'6RJ+aaIP5f7z3el02q9XqqrletesayWy6ohmDSfz8cEX1w99FCXBbKbDIRnXqQogp3l++Pzp'
            b'49V2mpZ+mD5/+Pnp6elX7794/823m7ZipFRKcapOhx6ZbrvNr979+vd/+tP9x6f7j73f4vd/'
            b'/glL8/LF++AzY3KZPSOpETUiOmft4uZpdjYts/lltQYRlRSEEMgpOMtRaynpqgshcM6VUoww'
            b'KIRSxghHSgggRcII45QzYMioIIwCRUBESgghBAggIYilJEyUkUIKBSyQBGWImHOMSHKJhJCc'
            b'c4xxNnMwhjBW1/XrV7dCqBSLCz76FLM1pQAFSinnlDFOUOQQcoZSMP8C/gtoqWjXpkCtTZgs'
            b'JJv8HFgoCFgG2ZrdbqXrbVvvr15cgVbggQt2vd/M4yXnUBCGaUz3d+fTeHc43D0fn4/nw3nM'
            b'ObuIU4gPzxdEjDF23fpmf9U0bYyRLAsWMBHM6RwjxJxYrXyfx3m2mD3N63nymBbvQrTB2ZiA'
            b'Si2qTOVKVi0VDBgFwXh2xdAYgDXrzejsw7l///b1zdubTSUrxTihz8eeuigVqZrV7dX+cjo3'
            b'dc0E7bab0U7GDIwWVSUjg8gjcZeyxPExOaFLzFul2/WKQtGQlsvxu3/8B0KlrjtK8PWrl//6'
            b'X/zL33zzdaXY508fp6Hvh+n77z9WP92/+/LXvNbvXn5xf/9YiQNF9nx/SPaPdgTGG4JyWUzJ'
            b'gtFqmZbLeZzHaRxHRLpMZpomAGjbdt12hJDog9ZaCcE5T1zM8+ycC+iFZrkUSZjWFWPsl7fI'
            b'ueCcM8KREEQEgFKwlEwIIUAVV6WklBJDhhwpRQDIKdiwcMGYkEgKASyYg/PWO05JwQKAKeX5'
            b'Mix0IkQgpVrrfnTLsjBBq6qKmKdhnoZxt99iIZhLyiUHj5AazlG0FEQpgpbAeZIUJYlKUinr'
            b'uqLbzUarDoBkY0hEKBTqBtHn4n22YQ6XsRdSCaa3+93t29cBy2UywzDEaapLqSoUQlgfVc5L'
            b'zOADBUq4TilN3m/XjR0m5ESgzoyMzhhIpkT75x9Wq1YrnkukUBjFxcR+svtGFKSAhDKhCKGJ'
            b'zcYEn+lf/9fvU8mY02rV3r64oYxdLpdLP/SXYZznGDIlWOtqvdqsum6/W2+uaokmuV7y+OrF'
            b'+s3tvhZcAJwfH/vjqBl9c/tq0zS79eqrt2++evf6y/ev371501bNPC9t0/5Xf/M3/+Zv/uab'
            b'r7589+b1F6/fMMo+fb777rs//e533x2O57pqXr56uWrb4PIyWUrkMvqhX1bdVomaIqMosKAz'
            b'/vB87M89FHx+eoKUlBCMkuCdWWbvLJZMEJwx1iw5RcFZpRVjtKQsqUQov9RPBCmjjDPOKMUM'
            b'hBJGBaOcUU4JLRlyTgSBUiaE5IwhYMkFATilgkvOGEFCkJCCOWdSkDJKKVJCGGWSi0pVSkoK'
            b'NOc8jRMhhFFqrbmcL+M4OGODC23VVLLSXObgMEUtqCQlh5mBo9lJHruKVRK0KNtN/ep2c7Vb'
            b'Mc68S8vknA2U0ALFTuM8j0IRXcthvNw9fESOL29f7K53BcHFePd4H0t68eKWMmqda7sWCgzj'
            b'aJ2bl8VHH0tarCWMOG+P58PD4f44XJZgTI6ZIFVSde2h70/9ZFxwKScgQERCruo149KYhTK2'
            b'v9obYx7u73Mp9J/9i1uAjJARwHt7Ojw/Pz1fLqdhGudxHsdxGKb+MlgTAAklBWI/D4/ejkrk'
            b'3brWtZQlCwRvgkBY1d2L3W636V7d7F7e7NpavH558+LFzc3VlZaaAGxX6y/evLm9vqZNJbig'
            b'KQ+X4e7u8f7uYTGeEPr25e3rV29qUR0Pl2VwlEhIOE1uvdoxJlPIx8P5eDzHGKGQ5KNWkjOG'
            b'uUDOBIAzprnkjDFCCSGcUEYoA0KRCMalEBQJp5xTQgkTlDLGBWWMslKAIFJCCaWEUEREREIQ'
            b'4ZdfDEoBhIKIFCmlNKUMABQI+X8DCfnlLIoUkRKKhBCkpWCKOaeklFZKKSmk1FWlpVQA2TsX'
            b'fcohEgBBiaAoGTaabVdakNhosllVu22z7XRdy1WrmkZvNp3WDWMKgOVMgo/TNJxOh5Ss1nK7'
            b'XelaCin21/sXL1+s1uvr25cZ8Hy5AELXrTKUxS6lYC5pXmbn3LzMxpqUE+N8s+3qRtlgRjOZ'
            b'4Aojsqnr9aZZb5lUPpXF+dkF5yJSqapGVx3nVSnFOIsIQvJ5Ho+Hg3OOKcEp4RD90/ORZL/r'
            b'dCt5o0UtRYIyD/P9/WPwsFpt9te325VaNSHYU4xzjtXS8Lpdbzv+6y9eVrT66cdHH9hms62a'
            b'umk0l2xeRhNt9kkS3mj+6JbPP/34O60vTw8xOMhlGIbPP/08j/0yGeLj+fHxxz/86d/823/7'
            b'X/5n/0VYyj/+/vthDNbDeOm9c6KIkkpwPjgfYwzWT9NESw7BpRhLKUIISlROJGNBShhjjCBC'
            b'gRwJRU5RcpEiIAJFIAQIFgIFCyAU+v+5BDJBAgglkwIFEQFyzvkX3WSMEQAAYFgQCwEEyIgI'
            b'+Ms+bSGUphRyhoIAhSQoyAkhVCkFBH0KkHOJiSBWStdCIdLoU/JB1pUWvJS55Ig5X+/3lDol'
            b'oakpZ5lg4JwKLobRcymgMMpICtl7b5w1brn0tmCqO7m/WrddXdUt7TZQ6P2fPw7DxXsbo7fe'
            b'WG+8t6UURByXkSEDgHmZjF06Z6qaM9YKQXQtM8NMWKEiZJisa1oVkJsI07BAyouHjHK3rknJ'
            b'zhlrZ0IT5I4TKhn33rEvXr2kAMvcl2i6prm62m5qLRnWUgTr/GLGfphm6yMk4GMPb2/rEhZA'
            b'z0g5H56jNZLW266Sb/Wm2RCU7WojBAOanZ+OZ+Of/fHUO5+WxZPoUynPd5/G06EEzxhBpAzK'
            b'tms3rTYhJWd//P0fb1bb91/+sy9fvYkG/vzT/eKgajbJ+sPpcZmdccFMZhxHY1zJkUGBXDAX'
            b'SilgyhhiLJmEViiSC5ZMCKFISAaIOYEHYIgESykpFiiZkEwpSYRSCojw/7D1Zr2SZMmZmC3n'
            b'HF9juXHXrKyqrqruFpduDgENJEIDjR4FLaMfoCe9668JkN75JGgkLqA0JJtkd3U3u6qycr1L'
            b'7L6dzUwPfrOagsZxgQxkxvXwhJubfd9nn1kAoAIq6FwvQZlRBGbtdM5Os8plrZ3fDDALE0Si'
            b'gInIAAgRAgAiA7JaSCKqSsyIME1TmDyAFEXhnEPkEKbDYQLw9rJdrxfLalmVaimoMqL3U4qc'
            b'mSQkGONkDCUFZs4JhtF3p3M3nGPyq1Ub/Pj48IGYEfl07MZvv9vthzf3+6ftAYCcK6MPfpxE'
            b'BFFD8Joil0xEqtr3x7HvcpouVkvj7Mx1Y4yGC+OKgqCsFxemQrRZeeqHYzcp7GJMF4smTEPK'
            b'3rm2bevC0TR29bE0P35xawz5cEGQXt5d3V2vNHo/nDSFnHyKE2gsi2K5XFZVJZKOxygxA4Rh'
            b'mA6Hg2Va1Ku2uUiTcbZeLRerixat5jyYKQNY1NU0+IPvmsLdXV0RcVM4w4DA19fXm81liNmW'
            b'1Tj4w+g/ub0zoPffvfKdX23uXl7dgNrzJFV7uT8OY989Puz6YZSkOWcmcrZsygI1a57vrhKq'
            b'ITCGDKGqzIqnZWQCzTGkZNgpIqABQiCjggyoVgEKFAFSBTYAs5qVFQBAUBRUVVEJARQAAIgY'
            b'RRFBFQAUEYgAgFACKc3vRWAkQiQDkHM2zhGXpSuWddWPXd/3u9Ph5uULSxx8/7Trcj674uZ6'
            b'c9Uu3DTuVXNOEqIAZkTMElLyoqEsy6pcaNb+1B+PxxQ9klxtLiTAvj+M3gNxFuy78TQEW69f'
            b'vvj07ublfr/98Pbd2/SWAeu6Pp/PWpZlWRKBKuaM0adp6A8pLRaLBHzc7vuQL27cyy8/W26u'
            b'6nYtirvd7vH+4bDbPT3cT9N0PIPjFP1giJ2lwnFpm8uLDRMYm8NmvW6ai7qubm5WVWFOTw+p'
            b'z9M0Zu8N6GrRuGp99+KFLRd+nMLY+wFVxLkEMKQwGtotm31bX66XmGXy05GyZBlyPhrW9aKs'
            b'fvqlT5SynLtwf/+43+99luWiWTX11Xp56PrKmKvL9WeLiz/8wz80MW0fd4MXp3r34u72xeff'
            b'v9++ef/0+OHDNCWJKfrAbNu2ZeAYpkVTQcwhhBgjKDgyTVVXZclEKAoARpGRCFBzTjmjAiIL'
            b'ZiICUkTMzACQFQQIkaxYdIyIAIgqUZ6NWQAgIvj8DzgrZ6RAiABIRAyICIryUTtQAUFVZEDE'
            b'oihERJM4y019sYjN0+P9NPX3Tx8Wi6Zqyhi0H/v7p0fnIMRq0RYMKGgyOwBRkDB05258/+FN'
            b'WxeLdm3Z9eehP58Zoart09OhLF0I06k7J5mvy7TVCl21vrhsmsVhtU4+9X0fvC+KgonKomCE'
            b'GCMRNc2aiBZ1U5qiKpvzOB32/Wnqxn7yY5Ck11e3imDZOmMvVitnePv4WBYUo5+mzhrT9+ft'
            b'0wMpDN3JD6PZP7y7WldXq5u2LQ1od9z13REkV84ayMu2ROSivmjbWtBOY5omPJ2VmerFerW4'
            b'CL5LPgAZY4xxLBCnmB2pQD/loyRs24sX119BtQCBdBr/7m9/sX188NP0yfXGWc4p+GmwjHe3'
            b'15fXn3z1+Wc1mqf2YXfsxVQFm8IWFuCw3b19/TpkyEKFNcwsKYigZkGFnHIKUUWsMeVcYNhI'
            b'FlBARM05AygRAZrnaEuAqMJgWFVUM4BRVdCUgRCRKM31LouklMkQIyPijLSYCBFVZ2ECsgIB'
            b'KiAgASohCwAiqooqAAApERIBZtWcEyuiobqs7q5visb99S/+n/NYrJaLsmBHMEzjsR+qypZV'
            b'RWhTyikbMkhECSCkviiXxpG1FQGn1A+9R1AAWDaEYHP2wUMMaYoJ1NQLa7I7UycRxn5CpUWz'
            b'lCKrKtS6aFrH1HUdEV1dXVV12dbtdXMZg7x/eto3wzRBCvnD63f3D/ssxNb5cSCiy8sLwlwV'
            b'XDr0563ELsd4POzC0Ktq8H6aJrPvJi+EpvCZnnbb/e4++6EpbFMXBMgVOghsypAppNRP09e/'
            b'+fp82tU11M2Pbm5vm6YJ04iCtqyMc8DEzGVpACmqH2O01sKyATYQxSzry3W9rEzm6vB03xRG'
            b'UwSlu9vr9fWlqxbM6Iwp68aM+XCe9ufXmcrdYchZl8vl0/5ERBcXFwBwPJ6cdXcvbzGEIKAi'
            b'AFraonCOBWLwpIBEhCSqEiIRWWuttVkzAiMAgqAKARAooRrGLAoiqpJznLWrJBkIGNiYAmGu'
            b'rYCKNEvuqjArFwCac0JEAVcgIcA8Za867/JhppRS4SzXlWpOKprVuPKyvP7xj3/8eHh42u6c'
            b'wbo0IZZlXS0WCztGzWny3vvRWltULno7JsdmURSuajfO2AyFgLGEm/WiLGxZGVWSpSmKJiTx'
            b'IRdlnQA1Snc+jeNIoG1T5ZzHsXdMTVu3bVsWThUuV+uiKCpXXF9ePT3t0ugleMdkiOIwjuf+'
            b'7/7qr6tFw4y3t9e3V18WNxeOU+nseYuS49D1McZxHCELAOSU+L/7H/8bsc36+oWA+edvvk1J'
            b'P//Rj9r1BVVtF+Tr797+6nfvXt8fpkRTwFevvn3/5le3N9UnL68Uct+dkcyiXVfNAsCEEHMG'
            b'IpsjHA/j9r7fboeUNR4P3Hd6PoxP9zmM66Za1tX5cNzvdt3QC+Aw+WEcs2QfYt8PMaMX6iP4'
            b'bDqvrz88fff6g8/K1rWLJue83+4RsKmaqR9SCCkFULWM1lhLyIAIYogcEQFIipIDoRKq5KxZ'
            b'UJSAUEE0Q1bUGUFlVbXGGEbJKfgJQYrSWYMGEUFAM6sQCKEiCGgCyAxCKITCqMagMRBzFMyE'
            b'yExMiICgCirGGhFJOWdFMta4wriSi+L2xZ2qppDZcFk2hauITMzoiqob/KmbDuf+YXu8f9r3'
            b'YyK2zjhAB2iFXFIkZzdX1y8+eXl1c8vG5aTMrmibZrFYbNaX11c/+eLL8dwf91s/9TkHIs06'
            b'DcP5eN5LjoUzjk23P03nnoVCNyKmbjxNYRQVQwgImLNKJMlh7JwB1OgKLBzFPF5fbyBhjtgP'
            b'435/RCJXOR+DLS3/2X/9nwfBtm7LsiDk66vLuxefuKr+8LT9zTffv3pzvzv2w5S7IZ6Og5+G'
            b'tpbr6+Xdi7vbm7vlalO4hk1puWyaJZI9nfr794/7wzkLA5Q5QdC83e9evfruzfevhmEorSmN'
            b'RVBk7ofp1A0xC9vCFkVIebc7nPvxcB6GAEpFUrs/T4+783kYQ8wxxWmahqH3U1RVUFRNpMpE'
            b'lTNmltIBDCETsQqCquScYs4RP/I8AsYZCwGRAhEaNkTIbBDnoqYqIpKJ0FpUyaDy/CMCoPOp'
            b'SJUAnoNSBEBB54yXEGZQP5dCJSBAZKLZlAOIbCwRIxskUlIQdLYoikoFQsqWi7ppFSgLKjAa'
            b'R2yAnQLnrLun3TiGjAymUCJkLquqauq2akOI4zgBgStcAk0gzhhLlpCenh4/fHhjS1vU9nDc'
            b'PWw/xBxCnDRlVPBj2D/ttg9Px+M+QVJU5xwgjON4Pp/Gfgh+CsGTQSYd/cCo3vfb3aOqXrSX'
            b'wafgQz8OWZKqZIllVZrvX3/nDDcM/MVnRiBF3T4du/7wi1/88u9/8Q+jD0nIgEW06PCLTz+t'
            b'+GLZmLbd1HWbUur7/twPhYkv7hrmMuX+YXdGhU+pappK0HV9h4iD1+3j9vXrh+urq5c3Lxbt'
            b'ynWxXQabtFyt1pvrarkcQnx82t8/HAGhqqlpVqmXU/e0PxyCT30/AmKIU87ZmAIRvfdkjRg0'
            b'hS3LEhE1JBERTMY4iQIAIimlkFKa3QqIQoZAAQGEEgKiQM4RGEw2oCiACKRZARQUJeWcMz1b'
            b'aWCWslBJlYRoRlWzeCqiAoAZgVREkee3z5pXBkAQJkKdR31AAIVRAQjUNtWS0UzTcCY7DJ0q'
            b'B5+DU2PIGMNcVFUTJefgUw6b20+JxTUlOuvDMHRT3/dD1/vNmlWttY5MSGG32/VhqKtFvhZr'
            b'CyFMgGRNSGHwU90sXr58MY2jZqhtZbk8HI7DcF6b1TCNZV05yyml4/G43W5FmYsCEIwxqoo4'
            b'XxUzM4qWTVk15WLVLsfF+XyMkmV+fNs73u+2Enycxqf7+8eHx/1+v90dsujk4+bqdhymx+02'
            b'TH4Yhrap7+5uqrIu3EKR/Sjb3eHd2/vvvn8bI+YMIjxMMUYFpBChn8ZRxFV1WTUx6ePTfrc9'
            b'ZAFTVGwKMoWtalvUaB27Miv0o386dGSqoloCVY+77tWb9+8+bE9dvz8cEFE0E1FVVZo1heCs'
            b'ravKOVtYBwCaRUQIgIhABBFFcoxxHrmZA4OJAXSWsmjWmggJGUEBkObC9axTADzvEcyqoJBB'
            b'kUAAEGDORoJAAAIKqhkAVTOAAOIseKEiIc4qPj3/ibNFkZmZmJkQyYeQQlJAa6wxlpBTTmVR'
            b'KwIgIxEbZ5xjNmQsWYvGorGCMEx+GHsALJwlpEVT11UTQ9jvj/fbx9PQp5xVuRuGkHPZliGH'
            b'b79/deq7Fy8/+fxHn7myTCmPo+/7frfbC+jt3e3F5rJpF8jc9cP+cBqnMHftFQmYRKVdLm9u'
            b'bouqLMry9uamcKWfJmOZLCWJIfnRj1kir1+aaRwxy9RP9+/e75/2xKZtlz/64iefffHlH/zR'
            b'H3f98Pj0VFVlVZTLVbtuV027rtsLU9RZzTimN28ffvvP3w699xGQTc5w6sfD8XTshj5ENfY0'
            b'jMM4ZUVA9jGPUzwPfrW+TMBR9Gl/fvX2/dt3H95+eHjz4bEbE5kGsHw8nF99f//m3cP2cDp3'
            b'wzR5doYQEJGQgg855aqslm1rmFBBRHQe2wMVEQKcAyvnPMsERESqBB/vOgIiEBIjAoJIRpxx'
            b'9++zkOREBKhCiKgCqgSKMBc6AZ0/RQAAUBCRGACAEA0SARICIRAQzQ0A0LnNjfAccMQsijGm'
            b'6JOKMhnDRhFFVRQFVBWzZBHICjGmYZqm4MfJDyH043Q6nUc/lYVbLdefffrJarGKPnx4eHg6'
            b'HFMWNMbash+m7X5XtfXqcvOwffjn736nBBdXF2VTIVHfD09PD4+7bTcOZV1e395WZcmGEQnJ'
            b'snPWFYAYJQtokqwAZV2nlLqhW60vvvjRF0XhYg7LdbtYNaIy+PF4PnTD2RRFQYBsLSD5IGN3'
            b'rppDu1i/+7C9urkkUxpXtqvlJ7d3L2/urq+ujFpbLjK6cQxhkkylqy/qxdVxzOWxN2Vt2YxZ'
            b'h847pzXXfgyn7hhHX7nCkcFiMY7e78774z/evnh5c/fCeH367vVuf3R1Y6vGlC2XrVf68Pj0'
            b'+t39/tiHmHOWsqmJCAFRNUw+pVi60jlLDCKSVFSVVAEg55xzJjbwQ5rC39cyhaxCQB/VKSVQ'
            b'QmERESIhQFX4+P6kQgTApDkhIkBWItWsSqqigoIJBQHm2MrPuE3hWcEHANU5C4IqMeJcYyWp'
            b'gGbGnEGxMs7U2E/9FCeRxGzZ0jRNZEvHhAhZxPsYpqHvz9bxFH3WoJBjGAlSXRYhaz9Jd9o9'
            b'fHj/eP+UNCnzMMTH/dZZG3Mo0sKCgOH11QYNDsEH0dKZerWwxxq7vlzWVb1ImM/j4ENApJAE'
            b'iZplA8baYUJnYhZTuKIs7x8fjDF/+Mc/v7m7G/vzMFWLxSJp7qdhe9pWp1IomS+++Hwax9pU'
            b'RVHlMh674cP9nm1V709PhyOQfvvq+8P+1JTV7fWVD6FaLoeou+Nht9udTqfofQipWV/5MHrB'
            b'0+CLAsAWbgEAEBS7bjr38bw/aYyLqrlYLI2tx2n67pvfdUHUlgrErrZVaupludhgtTLlYhzz'
            b'sffb4+nYDTkLMltrQ5gKY43lnJMxZjaFTtPESICAiArz3VZVTSoA5mPxUUSdixRIJmRSQUB8'
            b'LmoZNCMoikiMgomIZiszq6gkQNL5AxBVBJBBFQFIEfKz5DAnQCUiNKgAonPrBxFV03NsK7Ci'
            b'CggCREWcCQZZawiNDwQyN44IGbIKMLG1gCISBXJSSZrCeRjGk5fgnDWWrLPMNiv/+rffjH13'
            b'POxEpCjLcZp2pyFLXDValNz7Uc5q67pZrY/dsfPj4XQEAAKsFs0i+NKXzPY0DRUXHimGdB5G'
            b'P0Uytqzay/aSSzf5aAtHxhzPp8vLq6+++nHbtq++/93j/kEoI8Pgz0l92VZFW5if/vSn796+'
            b'7XfnU9/lKcYsPqbJp2bljqfhcNqezl2SfOzO/TgY45DraUzd8bTb7R4eHo7HIxPVdU2gyl6Z'
            b'W4WqKqwz0zScui4RHc7+3YftcD59dvfJ5vKOELrjuV1evnn/8OHxUDWtdWW7XBOZw6lv7Sr2'
            b'U3eOx1N/PA1d1yNb59w0+qE7aV06acWsiQAAIABJREFUuwQAy882TgninDOGiehZVRIBgJyF'
            b'Zqvev8hYqgoIgDKL5oow2zoAhIgRRAVyzkpskAhp9snovEmNAEWVCUVnm8M8g6jPShbMTTdi'
            b'VtVZ40IFBZUZbDETAAFk0XlQXyVhQmOMSM4pas7MaNgpaZA8K7eiSSUljaqZjJaO0ZocNY0J'
            b'kgBz9HA6IeTkiE/HoR9yWVeK7uCn7FaXF02adkVTTNHnIaPBQ3d+/eb19fUl0tb7sW2aRd0s'
            b'NxeqSkpj1/sukivAcpJ47I/AZmNNsawVJSQvrIXhsixffPry9vZ2HP3Xv/n6afvh9nRrC/P6'
            b'7ffbww6J6mXDP/uzzy83lwwUJn+x3iwWK2Ndu1gmFXJm9OPpfEIAkZRjrOr23f3jm/cflGmM'
            b'/h//8Zev375VxG7olOhwPJClpLlZtj4Fsnwex4BcN8t5nP327u7q6ma5Wn/11U8Wi1VZNwqc'
            b'MsQok49Mrl1tIpVZ7fns7x+e9vtzzM/VjUDLsrDWqGYmY5jnkCisUc0zYGfEnLPmBKAgMstY'
            b'M/6eAwsBmFBSSjmJZsNETAAgOc0aBCHNjGeOQ0RkYwiJZw74jJR0PpXO49IAhDgb5xGAEUBF'
            b'c1bJs+7A9BFsISIA0RxxiqqiYh2DJsQMJCFO3XgOyZNBJDGOi8KEOPipXyxqa+jp8W1FuS54'
            b'0RRlYQtLRekYYJqmaQoPT7sppXK5vn75+Y9/9q+q1eW3r18xB1cQMj1sH3/37e/O/ckVLqYA'
            b'CD5E7wMZs7m8ur69W1ysV+tVaavgfZBkrBPSkHNSGf0w+unbV9/24xSzNIvFf/qv//XLTz9/'
            b'eLr/9//X//76/fcPT4+7w25/2NvCbK4vyaC5vr4+7PYiqa7rECbNEEL4zT//dn19cfvipqyq'
            b'um1UiqZy0U9/+/d/nzJ9+tmXf/TznwHAh/vHh/326bA3xvQ+1E1J+0MEefO371MOzHhxeXXz'
            b'4gtRJFtmga7352FctqtmsS7KRtH6qCZkIpNS9iGcHh7d0ijjOPmcFdkUBSIySk45IM4JSVVz'
            b'BiCIgCLCACIoIpIVcs4zH5zh/ByU8wualSR4NliJSIxRVYGEiHBWCJRIFRmfW9pzMmJCpNne'
            b'jkwMM9LTH071/z/wXxy//8uZFigQwGy4IVDDAFlSjiIRMFuD5GzVlFOAYewYU9MWIP583BpD'
            b'N5vVdVsUDoGom8b9+dQN/ehjDHm1uhBC4nJz8+LHf/jzdrPBD/cvh8PTq/8Qk7qiKCu3WLWK'
            b'+XQ6dd0pCeQcDREZXm8uTOkM8QTUh4cu+pgiAAgDGhVKERSSlE05+G776vDllz9ul4uQ4te/'
            b'/vWrN68Op23T1Jfm+vJ6c/Pihgy/efPGWDYP7z9EHws2T+/vUUlVv331zfXpbsrTYtGMPtal'
            b'e/Hy8+z94fjLV6+/X19du6osy/LiclO3TU5ClgU0pjSm5EKsV4vz+fi4e3z39LQ/eVH88Pbd'
            b'7vHhfDwd94fH28f9/tiU1fbx6XA8A5CzRUrS92MfpISlsHTdOI0BVRlmkpc0Z9GMBFmVCOYa'
            b'N8cNogqmnOdMkSDLzO9EUBVzzqIZUJGMKsSU+NmCp5KSIjq2s0IjIggCAAQCiKogACiAqoJz'
            b'dUOEuYB+vIAZRT3TSEXEpPJsEvwYWKQKqoRzRwj12b+qAISo0U/I4JxBhiQxhGkaumE6ry+W'
            b'OOUUvSRWScEPBouLRd04qEsSY5J6M2SETCjWwDj2KSUGU5XN5dUNFIXPAoRZ8+h9kqiam6aZ'
            b'MQOi9sMwPxtZD2yLkKS0Lnh/v30cu95a6ypn1URgUciYnXV//NUfMRXffPt9zOEffvlPv/z6'
            b'N//nX/4fT4d93ZQXV5eL1bJdLTdXlwCw3T/NEwHi/ZQBfZiYuSzLdrUA1tEPZV1klcOp+/D+'
            b'gURPx/O577/+za+RTF23//zdt0I08zUAGUKqGuND+u//h38nEn/729/++Z//+S9/9SvLzk9T'
            b'jOl8PmcfjvvD09MTZRUBRuNswWwBgMgURZVSSjlMU5imyXsvSUUkhIkNMAJamGH1D4dAJsU5'
            b'LEA054yic3L6wZKgz1YXmEUHZmYyMzxKKRkj/9Gs88zs5qFCUM0y7zoSRMrknNOPyWjmkfPr'
            b'WdpQQkGdQZ/8fg4WBFFxLs2kmkEVRNGyNQTEhhkRY4w++ap0VVGy0XHoANP1xXrZNoXR64WT'
            b'PJ6GbugO/fk0DaOPWQRUBlTNaepOu8P+KTM93r/fb5+MgZxDCGPOmYjY8Gq1Ksvy9etXUwwi'
            b'4r1/fNyeTidmy6ASE7DatmwWNQ405THFDEDtuvnyxz968fLzT7/44hd//8u/+Ku/6Lvh2J1W'
            b'F+vN1erm+ootAaIPwTpeLBbmfD4DQN/3jnBzvWnKKkPmks7jIJBtYS6qzf3b91//+ncS4ul0'
            b'uLq53R+Pf/HXf+VciWDqetFWbUrpfD7f3Nx98uJWJLbLzWefvaia5d/94p9+9Y+/yjaBqnN2'
            b'3rwbQtjtdpTROVeXTaacsxKZunKuaj05FEOooFlz1iw5pRQDE7Mhg+zYzBvbn0MHEVBmjft5'
            b'zT8IEsJ82+eO8ccQQETnCmZGRE0phgSSwUcFsrYARFKcTS9EpAoiM/sDRJTZpDyzP0QR+Jir'
            b'EAVxbnkDRomIKLOKphnwuf6qJlKiLM/XhUIMqlgUhZJKyiFETepMsWxNRglhbF2DkGP0bVNc'
            b'rS4WbY0Qp3Du+/PjYbc9HHwM7LggSilJlLIpfNTt47tvfvMLWzfTcct5RFIGUNEkyYckoCo4'
            b'j4L57VPyqa3aqqwVJIaUCJraAZhqUdnS5jEFiREzk8mcjsNpE6f19WZ1tf7NN9+eu269uWiW'
            b'lpwM06hBS+vswdRNaQyZV69enc/nYexMXd3d3bRt/bTbjmlouCBLwFBXdd0ujrszZLy5+WS5'
            b'WRlXns89KBZFXRa1IsUMZdH8m//i33714y/7/vg3//ffvnv//ne/+93Dw1NVliAqkkJIgrFo'
            b'6rIsnXOVKef8AQDGuPlgoqosKRtrrSFmImQkIkZgo8aAsYw0m1JUREDVkvmYNuYen8w2kh8w'
            b'0DNsR5yDYwrespmntX7IYfjREoPPavyMsYCIMCsyZ1KeB3QIn8N69sQoKP1HkJZ+LHeqSjhX'
            b'7eerUhBFIKWPCU6IDDMbg8Zkzgmi5hjLooSsKSbLxpI9Hc5jd1607nB8GMbT/nzqx0FJjbXG'
            b'IgEBsWUDEvr9w2//aayXrQeQ2KfQ2xLbthYph2Hqum4ap5jScrk8nU5hCsxmsVgw8zAMPkyj'
            b'94KRJg7qOt9PeWS2VND+tK+293W7JC6HqY8SfAznvrPNogRKoin6vu/Pw/Fqs764uDAPDw8M'
            b'uNlsNsvFclU3Te3TeB5OF9cbdtawCTkt2pXcSvSpaRovvmpqUXpeBBVPmiiEcHV1VTWrq5sX'
            b'ZVf/L//r/6Z/E7fb7fbh4fNP7ngeuOs6FF2tF9eX15Z4FnJAEJ/NXGZOJIBIqARAICiZkdgY'
            b'ZVCNzyQPJGtmJsBnhv9RKZ/jSvA5xn7QAX5/swEgS4bZJIxETHPP6wfENvsWCOjZdfyxOUjA'
            b'z+QPnjVzFdXZHzMb5ZVUcB6Wn1PaD9FMz08CICKQIiA8a15ARGHyVW2NdYA2C0wp537qhmFt'
            b'lkKASpYIM56PhyxBrlbN+sLUZTJmzHl33MXoUZRV6qIMgM4UyNIdH/ruyZQVcmCTLdu6dIiI'
            b'qtM0EUUmQsXVam1MAUp9P9Z1TWQAYPRTxmgKa0tjCuMqp4oC2cd8//hBMgC612/fjdOUJO92'
            b'T1jkK7e0hQPBlHMapiOjMczLF+yMvbm6WayWIaasmrKez30M2dlKMkCmzerqYnNdupZdOfkA'
            b'Oi9NSN6HGLJIAtQQvUh0ztw/vP/Lv/z39w8fmrZatrXhXFe2LkuDaMhs1pvNamOZnTFNXTZ1'
            b'a4wRUUDrXGPLJqnJCkM37Lb7c3dWUUZGmp/1POcAVGRiZ521ViXOdw8BsmSJCREsMagSETGp'
            b'6uzNmvNQXTfWFYYZmBBQn/Wi7Kwjwzx76pCQiYmIjEEiNkyEz63oWfqU57WRH2kezh1pRPih'
            b'JThP7jMzG2LS5w4izTtHmA0ZY4xlJjYWCGJKUZIiELGxdD4dqrJwhTVMzhgFZDJV26wvVkVR'
            b'KGDX94fTcRx7Y7Cu3OPTh8kPzbJaX60UYoJoHZJJi9q6gog4pdQN4zD0IUVF9D60y0VV1d77'
            b'oetRwRqDRMrKhlbr1cVm41wpgiHIOAbnmjdv3r969fbpad91A1tbtw0ZnMIIhCmkLNK27aJd'
            b'pCyn44l/+vOXi8XKlFUS3Z/GX//2u9fffUB1kOzTu10a9fri9mpzW9ZLtC4p19W66wKia9sl'
            b'KKqKtQSYnZUUh++++9Wb1/98cdEYI+NwKgoQ6ZiiZKnK5rMXP7q7ftkWVVNW0Y8xeoBUlpVx'
            b'lQ84ThATm6KUrDnLw/394XAAhBBCSin5yMiaAUQtG1RNMaJmay2hMpExBCo5RRVBBWbkmd7P'
            b'QqOIITbWIgLMXUJDxEyGyJj59gMZwxaNYTIw73NANGzm9wMjMpKZ0XwGBAWVWckUAZW5xedj'
            b'RMNsDcykkpmYs6o1jo0hYkRCYEIzj8gaS8RKBslAljCFIeUAnInBWFLNCJhV/RTbxeqrr35y'
            b'e31Tl+Xj/cOb168O+11Vmk8+va2XBRqd0jDp2Gzq9rLJkBKGxbJ0Ri/Wy7quBz/uD4fj0Puc'
            b'g6ZhHHeHgxIpwGl/QsXlYgmqYHVzvbnYXFXlgrE6HobHD+euy/vtkKPJmfpu9DG1y0XdFApa'
            b'VXUMMSWpqnqzvlosVs6VSM787Gc/Ow/9drs9950AKZAo7Xenkj0jbs+74TQ9PR3q5UKtravW'
            b'FPazT7+o6iKl+O03v3n3fkwxEsli0bYLVxRWQVTz5eXq6mpdlfa0/7Df7TTGxc3l5eXlerGR'
            b'KYzDab/fK0jTNMakwcvxFIgXF3VxOnZsjbV2sWy7bsg5n49DjHFRN6pzVw6fBSEQBJAcgShD'
            b'JoC5CT0vAUUhAZmbJADwPFOacgJgVTKOZgiFaNAQGQRmmEsbwJzKlBBRUQEgIzAAkiLOli1U'
            b'kI+Jcr4gzTnOfUJNWeC5FM6bSODZCPEM+WZhAmc3lkrSrAkzSkop5ej9EFIUBETLzAJAiu1y'
            b'VbeLcYp1cE/bw3Z7kEyIfDoPxfZQrVyQPGiSYTLbhzVsoCKrTg0QmSwag+/G6TwNYwopqyKo'
            b'49PpeDh3mvJ0HplIorDjtm2Xy/WiXQGY/nQa+uQnkUTJYxJRBRXMItM0MKMSeO917kdknKaA'
            b'yLOZzbRtHXKYW2mr1epitTodzh9evx3G7mK5khQPxydhLbsmARZVuWiWq3ZxWS0Q+WKzmPwq'
            b'S80MTJA0awwh+BCnpmkuLy/r0hiS/f7E1q02S1uYMYyYUkzJFuUwDMejn/w5RB4GcUURoydr'
            b'BSGkNHrvU5y1b0AUhAzPbWadf55B1Xyj6aPjavZsyrPQoL+H5yAqKZvZzSDz+AMTEgHPt5wQ'
            b'59kv0o8KJ+A8kTFzwed4nnVR1Tm+EZ9zl6oKJGKD+RmqExPmZzcFKRHyM5B/JqwEAMxWSWa3'
            b'tDHOGsccIMVhGACgqgpEZGsXi8Visej7fnd6fPf+9Zu39wJMtj0dTrrtlrAIEV21Nha5qNE4'
            b'WxYhTKdxGFKcvM8q2+Op9yGKZlQV9N6PMRhlY40trZIK6aKtV7ery+tNXbdDH067c45JYppt'
            b'3jmG+b+fUuq6TkSIcRonIiKE4KdhsDHGnGMIwXz963+q2mZzvb795Prm7sUXn30epvj9N9/+'
            b'4m/+7mK1smzOfTeEmLJPAMf77RbeVVW13b5rmjrnuFovrOWicKLp6elhHIeYQ47ZbaoXdy/X'
            b'F8vjcvXu3YMfIjJP2eepT5Pvz4PlIiU/jj6kol0sLqoyRTic9peffBKT+BjGcQwhzGyRiIL3'
            b'AD886/iRuCmIEgPOLxAZCVDxI7N7Tlc0T3OhKjCSIcvPVFBVclYVxNIyIzACKxAiITEy8swX'
            b'9Ad2OZ/zB7f7D5Tz+YMADRjMzx1CQiABEkBGEFX8/Xl+/1sz8CdCJGtMU2rOmnMmHefYKgqb'
            b'ieY9vNvD4e37V4d+P0W9vL6uVhfC1pbcLGvpjxfrmguIeQqZrLFEIH56//RUF6UgDOMYsiBb'
            b'Qygioe9dWSyrRWFddzgqIjIs1+s5B4MSI1VVtVmtfR9SEgDaH48xRiUBgBTTNI4z15oNS4g4'
            b'b0Tquul8PpuY+k+v7r76yY9tURjjrq5WjMaxbO/fN0V5fXm9Pxx++euvJefLq2vr4P2bt8Nw'
            b'6LrdYjEvbCUydVFVZVk87bb9MCkKI7O1ddteXt2WRW3Lf3h4fLM7bKvCOme73n94ejRYSGTQ'
            b'grhqFpt2uej78X67G8dRkJCpqMqyqpjZ5xRimH0IiEBMwKSIICAic9IARAWBrDxbWLLMeil8'
            b'DMF5+TqqznQTdTbBIwDobN1jnUUvVCBCJrKEaCjP6ikKoKAQfuSczCQfW9DE8GyIQIMKs+eP'
            b'5h5hBv041TrPHSKR/hCHAEmeAZsCCAIiz99F07bt8XiIk69coarn87nrumN39FnKdlUt1qvL'
            b'DSJS2drCkIF61QPL7vi4PRyb1jUXq4v1qizLw+M2I8WcxpiCKJnZiq22KIgIGLKmpCmE1I1d'
            b'ylGT8WNgnCpXf/HpF5v26sXtY9+Nu93BGNOPI7DGGH2cMuSUkmPOORNiXZQ3l1dt2z7uCu8j'
            b'//F/dnv3yd1Pf/qTy+tLkZQkhmk67Lan42G5bH/06WdVXd4/3ndDV9als2YaRyIEUGOYCIfR'
            b'q8JisVyult04Df0YQhQFY6y1BSKPg3983E5TTwasZWtZVL1PflQ2DZsaoECaF8DasqmTgiBp'
            b'1sPxOE6eiWPK83Y9w0wI1tqyLIhIcgYQxmeQrlkwK6hClpQSP6tH/0JYAhBBJjs70JkZiWfN'
            b'YSaC9Ax8iOZRxHkhw1w4Px4fK6w8p8wsAhlEcZ63RoYMkmXu4SCSgs7xB89RNTuyAACQCBjZ'
            b'MBuLSHOBV9UUU4hRRIZxyFmqqnSuyDnlnIGxbOtmuRAkH1I/hinklHR/Oq/Wm/Mw3D/en89d'
            b'u2xuPrmt20YkSZKyqKLoMEzTFAQAkQBUc551tnmmVkUkS0pxsWhjymEIRLReXlRVk7OkmEU0'
            b'p8TMVVWWha2qyjnLRCoyO7/LstxcXi6Xyyziveef/OkypmCsQUIfp5mCd93p/u3bxaJp68o4'
            b'RqK+P5/7k7W2cAWoppzLsrSuHIYpZ2hX6+VqU9UNovE+IpGxDgS9j0/bPSIZSyl70MDWADGA'
            b'zZFVHVLJpgTADFLW7uL6UoCV2E/h/uHhdO6YKGcgopwSG8NM1tmycIgYcwIRi2SQEBBE8XmQ'
            b'UFJKTDz3bxBR/sX4Ms383jhjLBtLzMRMhuXZCYMz3Xu2H6jM5s+Plr0feEN+tj+oKAgDzJva'
            b'ZvFhjjxmIkOqoioCAgSKKgiKKrOTdb5A+ywGz10EZFSArHnou5RiTtlZW1YVAKpK1VRYsBKd'
            b'TudhmGISEcoZDsejMa7ru3EajKF20RSO+/G83z1ln1UhhjQOU/BhDl9JOcXkyBbGODbGmNmW'
            b'aNgg0XF/fHx4OJ96yNqf+9evXr/67lsmmvwEqMiECGwYCUUkxZRjnrwPPqScY4znrjudzuaP'
            b'/ugPHrZP33//3eF8YGNWq1Vly+NxL5pjDG/evW7r5tNP7g6n/TevvquqYtmWYQp+PBdOqtqp'
            b'0DDFvpseHnebzaZpV0SPmJWEh2GMMTKbonTG2ePZVyXakuKUu7E7jzn62FTl+nJd16WoF1Xk'
            b'mUchGSbDzJxBZ0foD7hk1oZmqqWqhpBmYeC5JP5/QAwzA+G804MRgUnZKJMYUibl59+bvTAJ'
            b'lUFUIYOQiCSZ1VNAAaUf3H6gagRUMgIoqkFARZQsKiLiXJ1UAAAYkEFAFRQRsiZVAEUBRSCe'
            b'x7MJISVmRCARVVRGtmwqV3TEbb0Ypj7GNKeElAM5VtCsUVMui3qxWBVlpQhFXR1PWxEobB1T'
            b'Oh+7aTooxRyDTKm0xUyUDRrN8+BHMsiVKxjQ+zH6IDkvVqvb29uQ4jT57nROUdeLjbNF13Wn'
            b'00kVfYwAoAlCDsikmlNKRVFoltGH/f4whXg8npHZe8//0//8315dX6WUkDBL6rpzDvHp6TFM'
            b'vj+fl4vlp5++FJHXb77fbbenU1eYsuu9s9V/+W//q5///E9fvvz8H/7xV/0QxiHs9wdGbtta'
            b'Ux7689D3h/3+w/2H/f6JKN/dXi4Wzc3NzXHfHY/D4TgxVzEhW7verIFUIG+uLi8ub7thSiGl'
            b'lB7uH8/nszNFjBEBjDEI6pxr6lpiGvuBEApmkEyqSEAIIllnH+Y8sGANMwMZZEZkIKSi4KK0'
            b'ZcnWoWFBEBIhFRU0RIaUQDRnzQr6LJEjGCSVlFOUlEAFQVKKczLLKWgWZjSGETEDxJQAgZwB'
            b'xphTVgFDCSSpZBAlAEPGWbbGzDHF89wLKWiMMUkylgF0fzzEFKuqSjnFGI0r2BBQXqxaw3YY'
            b'hhwlxBimuGzb7ePjw/3b/f7RGm1qZwi8H/0wnvenFLKfQhgnAqydQ9EwDAz4+d2LqihJcbVc'
            b'OevqqvzRF19UdT0M07u374ZhautWRY/HU0qpaVokSil1fXc8H4+n4zCMWTSGJArM1hjOWcdh'
            b'8jGqgrm7e3F9d3s4Hv/h61++efu+rtsvvvjyT372r6ZT9+1vvomTX68uXFm8fv3661//NqVp'
            b'hwdnSlMVzpaXFzebq0/ubv/D67dvEMmadVVVTbUsGI8W+vPh4Lu+O0yTFsWSuL28vHTOJc1Z'
            b'U7Oon+6PcTqxs/QAIYwvPrm6ur1dLK77McYplmVZ13VK6dlDpzAvR0ghxsk755bLZZxG/LiX'
            b'4/dUC4GIjLMw7wNWBWJiw9aSsUVTF2VdVpVzDlRz8DGK5EyGkqSUEwMys5mxG2RrHSMy6Sx4'
            b'5Bxz0qTKzDSboCVrjklZc1DkorURVCEn8TlFETGFKyozxYAMSBnnbSOYkBkIC1vP+qxoQkFE'
            b'ZVRRsMZY4qjPex+IiJ21lrAwpMCAzlhrCiBKUWIIhXU/+uyLzWUT5PTu/bc+ekn53as3lxdX'
            b'OQpKRkHDjEnzGOIQvvqDLz97+bmq9sO5rtrRD6fT6Xg8C+h+d/Q+1lVx2B+Ph1PXDTHGaZqm'
            b'ELqhPw+992OSrAgITIjWFNY6YwsT4+waImKTkqhgWdYqOH89s5/if/LVp3idWc3923d3d58s'
            b'l8uHh6e//ft/GkavitaU3uff/vbb7VPXrNbeR2sLRmqa6mqzrCuHufe9DDLG6ViYrKRVWcxf'
            b'X/T27fvD4WgKx6YoBx+jv9+9OY+H1XqRdPP+/kMU23Vd3/fjOD5Li/JsaxERawxkGYbhcrMp'
            b'l8tehSXPaxZUFeahZUMoiMyqKkBEbJwr66osa1s4Lkq21jgzSwDCqBlBlS3lmHLOQEAMyEYg'
            b'J1EFN3+fF4ASioCmFEWS4XLGJQSSspcMkpkM9wMkVGPM3HxKOSXvBYItCzJgDBmrbMSwEGdm'
            b'IhYiJgZUNIKgxGIVBbCuqmoMY4zRZqcKcfIxY0lsLVelS6kah9idp5ylzOWf/smffP/222k8'
            b'7w677eP++u5ivVk+fXgk4MJYyxVqjj740UefDJnCFs4UqjriOBuWlPrjqUPE3fEkimR4dzww'
            b'c9su15ebrutEU0op5zwvTc1ZMkRNUJaEzAIQUhYRYwwYMq++e/3q9Vsk8/i4Dz4N/b4w1b/5'
            b's+XVYtO4Zjr7GDNT8ZMv/+CzTz57+/7eukVOst/vh8l//+ptVbeHw6EsrGj8f7l6r15bt+Q8'
            b'r6pG+tJMK+50YnezT3eTzaYkCiZA2ZZ+gGSAVwYM+K9JlwZ8YcOwaVmCJZsKlgxRYrPZJ5+z'
            b'48ozf2mkKl98ax/SmncLC3tjLqAwRo2q931ePxzX6+s9pN3udjhuOR8JxsKAENROp+D328Pb'
            b't1cpytMnl35kZijLmJm0cvWiySLffv9qvRm7dvDet23b9z3HJNpwyoZUTkk7q0mlGMPoi7kr'
            b'rMt+eDSBAsjjdPtxLYiKtDa2KMq6KuuqLGs02pX15IkGFiFyzhTWKBTvvSLNTCiiEVmiiEiW'
            b'vmcN+EjNB2GOAkmAgZMQKyJFnJAhZ0AWAYKkcHoCKiQCJQwpJ6HIBAY1ICAJcOIMCbWFlLOy'
            b'E4neGKT3QjEAqKuq7Q4pxDB6VCSElnRMKGMgUFpZrUUplVIex/Hzzz/fHTfGQsogrA/b3tDy'
            b'g+efbjf3s9lsMZtzSve3N4f9XiPN56ux6x8e1mPwm90GlRaU3o9a6+PxuN/v67quqmq/P6BA'
            b'Xc8mqS0SkdEUFSTkNMk2FBhFugCywpxzjDnzFPSy2ezbvgejur4ffQwhpMRV1TyZPTtuDw8P'
            b'mxw5B0BFIrjb7etGpSghBFdWzjltqCzdMLYV6fX6XXd4Yw2v5u5nP30xn/2oH9pf//avrm+O'
            b'2/UNkVnMYxqzKUpjVFlXqODy6fny5Dx43O27LFjaOud8cXZW2+rm6jr5kHMW9ajXm+Sa1tq+'
            b'893haJU2WkskARGWaTpPiDglRYlorWxVlnXlyloXjgkBZDoIM8fpHiMUEiCUlJJCNAoFJMWY'
            b'cwQAJSAMCtBZjeAIMMUoKSMBiEIwhogMcQIfonAiZGVoGhaEQRlrlVJCiExjHMU5hIxiISki'
            b'YqKotNKFtQUpURoUqfcLyAzAdV3Wfd0NA5FGJG3tbDljSkMYIDMoXVSNKeu+7/ftoW37ppmL'
            b'JNLqk49/miUIpGVVd+3BOVcURY7RGKeV1QTOuQx4d79u+64LvXJFzKEbByIK3aCNffL02WI2'
            b'70cfxvFwPB6Px+kPyTkzp5hSyImIlNYnq4ummc/nc9RqaLvNfnM4HPpx1AhGKdP2vh9iBsii'
            b'bu82/8v/+k9/8sGn16/evPzk5c8sAAAgAElEQVT+zXDhNRYppfXdtt2348BV3SDJ8bg/tn1d'
            b'165yOQFCjKFL47Cc6edPL/74j3/12U8+Fsl/9m+f//N/+Wfff3d3OMTuEMpqhpGvr6+fvXj6'
            b'/KMnq+WpgNk8DKZXIERaV65YLBbI9CjHyyyZNdK0RZ7ebwrQe9933byuiEgedzxARII4veFE'
            b'QBltnCWjs3A7PCpxg08ETIBIQjIJQzOnRALakFGEIjmmnCMiKsLalgQCYgEEWEIcScgYxayQ'
            b'yNjCAOYYAgpzxgxDH4FQK2WIUCLHaYWejLPABUHC7EQp0kprTdpmgKQgRqUUglI5S0oxpaSM'
            b'mdfNMAwxZyLKCCKilM6A2oIwjuPYdTsyWmttXfHpj39SFPb6+t3D9u58eaKd3m3Ww3Ak5XyK'
            b'x67llEmrZj7jHH2KseMujCHGejk/e3IZgePNzX63IyStLU1JGTGGlHQIvR+998ZZYwwqIqO1'
            b'QqWUtuXi5PT87PKDDz5crZbe+9dvXn7xxRfv3r3RVdVoZ8e0tZaH4P04Hne3X3/+9QcXTytb'
            b'GCDOMI6Bmc/OLja7vY9Za21tDjHvDuvN9u6TTz5aLJuu3ZyuZrN6pnAMYXfcX3Na1rPZH/0X'
            b'v4o5fvjs+vp2//LlTVk1Mef9YavuZH4yG8b93f3+uM8xGk45jKhPjaZdu28JoKnqliXnrJFE'
            b'pCgKEBm7HhG0UhxTCMEYARFQBPDo/ZsEWZNoBREnWmnIiUWIyJKaBvIEkzQGASgDDn2bQw4C'
            b'zGmCfEwnmSqZQNjGnCPn7P1glUUskiYS7SZPPOecQs5ZGe0UkVZAlFIau857nziLiB/IjC4O'
            b'xXTrWeeqqsIClLHMKeUQInBWIpg5sWQF2hWuLEs79KQN5xRj9iElxWNM4zhuttu+H09PT5dl'
            b'rXP66utvLp5eVvPFhTPD0G3v7w67PUMnlCgCg+SYUKSsq5xzjHG93SbOaLUuyubkxJVFJOpj'
            b'7NebOIx3D+vZbBZSHkMEGKcJDhFZa0krW1SJMwCgspyBAbRxq9NTrbUgTIZT9Y/+279XNZUi'
            b'Ms4c9sftZlvaGrIUplqtTheLJSCdnq2ef/DclPZhc1fUNmSvjPnok0/Ozi5ijHVdFIUqCvns'
            b'Zx/+/GcfaRsf7l+33RoVJ46ZoJrVv/zV3/mdn/687UJRzZQymWGz33XdcH31sN12Oen9dtjv'
            b'h8LWxrgYYtv2YYwIEH2KY5gUmYt5w5L6oTeGnDWIAgjW6h9MMY8rXkERIUJtjNaK8zS+G4Gz'
            b'RpAwyjgkP+TggTMhE4EmMkYR4qS6UQAKCYFFJMQUc2ZgEfFh8KMnAGuMRnLGNU1TFdVkudeG'
            b'itIxQOC02W2+f/Xqq++/fXt7e/SjF+68H3wYQxj8GEbPzBqAEArnEIAkK3iEdaEwAqScrDEh'
            b'hBBjWRZaaQQomxoVvr159+13X99v7qtZ9ZPPPl2czLb7ze6wfXi4A5Tz83Nt7DgmnznFNPpj'
            b'WThnqpw4J9HaWFdoY9fbrS1dUVWmdGVdl7MmCvthCMcBGU5PTp89fVoVJecMmQFFKbLOFoVz'
            b'hTXWaqNBIQKF4BHEWioKYzTFMB6Pu3Hs1T/87/5IG5VSMFrVRZN9bg99346r09PlYrk6O9EO'
            b'VaHR8nHYVQt39nShLP7u7/3yj//4v/r0kx+PQ3jz5ntXkNLD5ZPqw09WJ2dujIfb+5shBjer'
            b'V09OF6enZ5cX2hXHcXz95nr0abW6nM8uHu6O282oaSapGDtxup41y9OzC+MqZ6r+2F+9ve72'
            b'R0TMOReFFWQyqA2ENKY0aENFoYUFhQgfNzMigswI4qxBhuSD7wc/DhwDMWtJJgenoHK6Ko01'
            b'RApFsoCkHHz0IDIOY9d3OSZEGMYQQPocxxD6cfB+FGYtigRLUzlTFq501hWFtU4n9v3Y7Yf+'
            b'u1evfv3VlzfbLc0W1eVFD/R6u2lFtqO/vn84f/KUE5PAvG7ub276464gqIxROUkKhgQFgh81'
            b'AgAbo5WiFNNjCUq+2159+e1f7Q73GX3IbblQRU3r/c133/yVK3QO3mhdVvXJ2eWnP/ppUVal'
            b'LZpiJqwNVZIxJlHKtF2bhOtZVdc1kOyPh4f7u+PxoBj7zfFktvz57/zsZ7/zU2v05uHB+2E5'
            b'n0nOs6Y2hd3utolTXVeZMyLPGjOfO8TAeSRK+/393e1VTqP23jMP4zgaXSxm5ccffjKr9+/e'
            b'XsWQSJvl6QlzKis9P10Oqd8P+9Vs8bPf/UUKbr3bPjv/6MMPP3758suH9V1R+t2+7IdFVavl'
            b'yWr0MYN52PYvEiiRh93+9au7q+vbbhi1KlfLC2uaqjh7uNlst4f90CmyZV0qMq6odpt99qEq'
            b'y7PV2bA7eO9La0TyJBQA5EdQ4yT/nJRXAACgHj8aHicQUTJPTkNCJEZIyRjFaRzCyAMiaVaY'
            b'GBNna20YPcekEXyIEVN7PA4xgnOMoBGcUo6wJGPRFKmIgVNiicAMyJBy9t4fu+6rb77vU6rq'
            b'WWWtuGLf9Zu23R1aOvbPLy/KZnFx+WRhi367Hrpx0cxub6+Jc/ZjUTVlXVmlyJDVKgkjgEay'
            b'2mQjiRkBk2SOfrWoQj7s+22f+fOvxrc3X439sDtcR98tZmfz+byeLed1Y2xdlYvyyaeVA+8H'
            b'P3bHdpvCkHLf9qHtBm21dZBBRu9jToJADE+fPrs8Obu4uPQ+HvZtXZTLWTNfzK5vbwffo/Cs'
            b'qRI8ytGM0c6p588vq7Lc7fdffXm/O+yv393sD0etqAh+8GPyMjJ7EH1xcaGV0doqpUBUUdgY'
            b'wm7b9h2niPN69fzyw9vrw7uHt41pl/PlZz/9+fevfhvTw8Om/c1vvjk5nV2cX/zB3/qd9uiv'
            b'rm76f/UXy5OT6On+rl0/tJJtZuKsdWlAKOSUmJ0zVdk0s8o6PfQtAgPnse8I5XS1PB6Pu92u'
            b'qJwwA8uk4zQ4YRHkvd1Z3tsf1MQInehF02hqWgTlLJI5RUgp5CwZEUkHyaPP3vumaUQEhZ+e'
            b'X+AQjaZ2jKjNMIYkrECyJjBaW8yCjBhSjJlD5pQZCGPmfvD7/VEBGiRlja6qpFQefEVGNw2h'
            b'/slHnzxZnf7hr/5WgfSbP/9/r9+8Wy1mpih95s4HcqwYMGaFEUlzZhZRavKZUUg554wSrZa6'
            b'0vLg+3bLml+/Xk96lcy57faL2ck4DOu7exG3WNkPP/i0cqAoXF29ffP6sN91AlEbAlFKOWEa'
            b'h9j7vu1bVjifz5tm9tHlB5dn52VZXV29vXtYN/Plpz/68ORkpT///OtvvxnHwCDejzlnY6a7'
            b'sSFdMutD62+vbraH/dAOGVArKkFyTmoYhuOhq6rml7/81d/523+42ey++eabw+FwdnamlOMM'
            b's+akrptZXex3A2f14x99Fr08ffr06bOzH129+PWv/zXq/s3rm1cv3/3qV3/w4Qe/p2D8/Lfv'
            b'9u3m+qrf78a+y8BuvxuPu217zBfnz7bbrVLm008/LUzlx6SUmzXN3e01CfCQ9tuN7w7WmNoV'
            b'u+mEyog8JRU+xuKKgNKPRHWc1CmcYmYARlTMiZkFMoJmSSlA5hhHD4q0sqKRUx5DPLTdMAYh'
            b'M3ETq/lif+wEMGQgY4AAUmKJOUMkyY/Sr0kOSIyUmZAlMY6Bu36sy+a4vj90e1vVRTMzIiUo'
            b'qzCMMR17qZrh2I4x5SSuLGxR1It54gzagFKAKiQmYG0kA1AWZFDKWFCEKVASycvF7Gr7/dBv'
            b'U+oF2FijlJLsC2vHzitiySnGKBlA8GR1/tnvvEihs9a2bXt/f++H0Vp3cnLRXw05I/iUQ0ZR'
            b'lbHzZn62OqnrmQ9pvX7zzTdfdYfjTz/78cXFk5OT5evXrznl0A2J8xjD0rl5VRnrxj5+/cW3'
            b'zDx43x3742FIKRVFoYMXP3Lf+WEYj8fO+5hSOr84c869e/dmHMPh0BpjZrOZIgiBFFY5pHmz'
            b'+sO/80eHQ8ec3r77Him8ev0FqjqldHt7/ZvfvPFjbVXVtgbHPPru7nbrRynt4rD3KRJR1R6H'
            b'upqfn59fXl4y093tw9COKYexPx52e/CsBCSnvh2E+eJk1Qf/1wpPnKydappvkUJEQZoWuTxx'
            b'GYwynBM/igsS55x8HGOQyRRkDJCKMfkkGYmMPTm/KMvSabM8u9hsD8EPCUDhIwsSBLOgALIA'
            b'CyYG0BaVFdSJERgENJJB1KTAAClBK1STKRAtCIu4xuqQ+93hu6+/Gdq2qcuPPv7UOXfo2uDH'
            b'nNEnoAwobBBQEyAlJshiCJVSAMRICNm4OnuvAazBduybxfLy8rRt+9DFqnakZPTDyUn10x//'
            b'pKhPgHk2XxI0qJXWehz7r778bdv5lPPY+5xzWdmmmp0UxjlXNrXVbr/f7/f7u5vr9cNd5Qpm'
            b'btuWYxi6ToM0hRORpnDny5W19jj4/hiGmKYdmiFXuTqpJMz6pz/92W63Y4b1+j7GuF6v//2/'
            b'/39ub6+Xy5N+6FLM+/3+9OT82dMXiOru5uqbr74rimK5gL7vLy/P7+/v/92/+3fH9oEZgs8i'
            b'rihONg/Dv73/y8LMXVEd+y0ADn0W1hJEclGVZVUujaZJd9t1XVU1q5PF0PbffffVYjY/mdd5'
            b'TP2ujX5UwkqrGLNTWiY10yRxQCLSKJA5CRDqCaI2wfoEGVOKzJxzEpGJmRWDjykaWwJQypJT'
            b'8CHmnI1x1tH93bqqi7oojabNZhN96AavQjKFRqUUkzHaOVcUlXGFsSXpQukC0EwnFipbVPNm'
            b'vnSKiFTd9gBEymhrz1ztqnK5XIqIK+2smnFMl0+ezefzvu8pJiWPpCIKmTQKMihQVgnLJP0i'
            b'rUQyMqIoja4uZmcnZ3mX1tv7FH1dlYowmHi+eu5w9vbN+lrexN/tnz7/uBu6/X5rnSKiejZr'
            b'mgYIvY8xjVpbTjGMvrCmckXTVLZwmvT9er1e37fHo7VmPmuI8/r25j6H7rCflUVVOiIi0lVV'
            b'rdfr7fVdH3Q1Xy0XS4bc87GcFSxpf9zr3/3dn3vvRTIpbmZlyv7m9s39w9VisWzquTFu6MPl'
            b'5eWnn356dnbRHY7/8//0P7787tXlRfqz//tffvjhx1dXb3/9l38eU79YFqPv+j54jynZ0XOf'
            b'R6QkAM5ZZ2YgyuhqNitRaLPen1+cHNv+cDhYq1erU+fKMXofRqT5YjHPNhwfHoLvZkWjyQz9'
            b'zlnLCBkABdRk7gOFyESoQJAzggBNaRCgFEWOAEzAPNFmhJVGgwYRJ347kjLGGFsQadTKkLLW'
            b'VlWllDo5ORFOJ6tFSml/aImSFigKW5SVLUrjSm0doBJUDCokECJlymZ2koVDf6yaFBO3bc8h'
            b'1UBlZSpTpMFXTV3Y0lp7fvl0eXY2jmNEIF1otDlnQUxMBjSSyQBqEt8zEmkilRJLksysjX5y'
            b'8iKkvGuPhasJbYzRWruaLy/PLsYDA6RXr7/9V//6X/wRUzVrvv7mgFqGrl2v72/ub4igaaoQ'
            b'JYbKD21OPoVRYgHJYlSSWeJYGDLLOVIuteXoh+M+xQHHodZqUTjn3KxutNbcHmI9u0uhRD1T'
            b'VpBBetJoXVkR6vuH26oqQxz6/midXp3Uw3iMMQoEpRkpxzSmFDLHpqrOq9Xf//t//5/843+s'
            b'Nb18+d319bv7h2vn9Hyx6vqds3WI0j90Q5/KYgnKHA9DUThOBpXRyp2snnz00UcI8ObNq7Zt'
            b'icQaxcy3t7chBGPcxx9/vNus290Wxwggzig/9miKZd14zpkZ8NG/QEAKEUFpjSR/vaWeNoXT'
            b'C3Fq5n9AzUybLp+SQtBGOVcaWyApAMogdVEyszEmDj3klGLIIR4PB6U1MinC99ZWzQAxS4Ek'
            b'oDKDABCTUaaskCE/+AGVma4eBF3YEliGrluenMyb2Zjy0Pt6OR9iut1snCv7kABIhECAhJSy'
            b'yjhjzCPe7T25dMJMhBRtWazml/fbHbE7WTwpSx0D68o0VT2M3X7fzebFsfNffPmXZVmeP312'
            b'7LdEsD9sD7vtdvegUOaz0o89cEJgq1XtTGkUcRyOQ85ZMc8LS6UJwacwxBFBgwEOHJCT+MFa'
            b'fT6rm6ZpCH/8TL+96fdtKFxVFHaGKiXfzGt7eaH+wT/8g5cvv9nt17vdQzMrnz49f/78KXP0'
            b'fuyHTgRI4e3tzdXVVeaEmr/44rcxhCTxRz/+5MUHT09Ol9rAenMHBD6E/a7zY0Iw45Da3hNZ'
            b'ZfR8foJkju1YV/UHH3xQVfU4+pcvv8k5aYN1U5+sVovFEpGGvttu10N3xMw5pv7QokhZVJNu'
            b'XEAA0UzAFAEE1IqYI7zf2hLgJPsjIqPUJDWeIse11pOfVCtttTZTMJgIMkNmyWleVk4rjYCS'
            b'OYbox+h7QCyLUpPSShXGOGuNtkY5rSwzOlcVRW2sQSQg0sZUdSWQlNFG26KojLUg7zm4gt0w'
            b'ROEoMqS47/oM6GMEMTFJykLKFGXpitJaR6SUNu9JXUhIINAPw2F/LMsmJdzu990w3qzvgNBY'
            b'2zTN3c3tfn8Yu7Hvx5gjSx6GLvPAEF++/Hocj2/efY8cYxi6fl8UOoVRKyFJ56eLj188S9Ef'
            b'tpvK6dPloi6cATlfzudVkcfOEhQaa2fOTxYnTTNzRe3csmnOFovGVSfzJ8/On1cKZRwKRY1V'
            b'paGTplJ/8t//vRhHVxjr1HzeLFezFx88vby8+PKrL0lRzvn+4e7771++eftqs3l4uL+rq1IA'
            b'iMA5c3a+ev7iiXN29IMrCq3NOIS+8zkjiBbAiV2jlAYga+ysmQHAzc3Ny1ffde1eIMEjmkxN'
            b'FmFldFM5BMkxhnGMg3fKFLYAgMeGY9L00mRyJkJQIvje/ULvnV6IqN675n9w18jjUIIJQSFN'
            b'bmyrjdOmMEYypzD6oR/6No4jSrLGVEVB2iCCITQTB4CUQk1KG1U4V1dFpZSZ8jgUTWHAADQx'
            b'QpRSRimjHiUWFRlH1pI2oLSQEgQAJaxRJiuGMcZZU2ijldJIpJSe0MrTiDjEGGNUqqyqRht9'
            b'v12/effa1SWSxBi2281mvWZma1RmrptiuZz50FkLfX8Y+n2Ko1aikAEYOBRWoySQWDlbFgY5'
            b'knBdullZni8XJ8vZvK7C2Pu+PV3Nnl1eNIXVABqxstYqxd5n70mMksKS1QBOkTVIkhTHwijt'
            b'w+H7l98SkdaWlGDHStFmu2nbgzHO+9i2B8CUkt/t77fH1WxWl3VpHEUeD+0upPHYH4qqtK40'
            b'utg8dCLbEHxOmJJk9EpJCL1z9XJxohyu9/cPt3e3d++IgD0gslJEpBpAZ+uyNHpWaq1Gezyg'
            b'liFB4GlYRQSS4hR5ij/Y4x/NpRP0lgAJgBTQFHw6uW0YmZEz5KwIIBqlkQRhej0GpjS54lPi'
            b'SfRsSRunBB7F0AZVEmRJBI8wt5QSYtSYYow+ZtJgptgUJCKsmzkRECpno/cx+pRzRlLKOCDF'
            b'gEkAsygSAkOkSVA/witIo0Ke2MoaQab6BQCRLJIRxRiDLNbajz/+5PZ4+/n3f6VI9X2XmcjY'
            b'cDhwkYQ4c4+kfNy8eXf1KXyaY795uLXWciZnnTUGJRZWDRGAuT8cbjk4qwtjtIjmrDlr0sxJ'
            b'YsjBT0vG7cMaRAhwpN6SQYGUUo561rwwulIam8LVQHsOIaRCKX04rq+uXxVFeXn5FIDbtt3t'
            b'9l9//bW1Rc75eDx672ez0hgnEIehe3t9NZstDGGU+ObN65cvX242m6aZnazOYszD4GPgEFKK'
            b'nCOjAibPzEUcjEGlJWfph71IRJq87jzJx8ZxBNEiFgjmy9nJbLmoG51pe7sOcbSmeBQjZJ5U'
            b'NI8WU5H3xmJ6fzwhTZZUJCIgIFHMWYjS1CZN+gVhfJRksUyWG2fcI7BfT3axlFJKwsLEmKcu'
            b'TlJmxqQUSCaOo/XeR2sL/ciLVESgFGZb5YwKAmEiDDlnBhKkPLFLEz262JRWYDQqq40xhjQq'
            b'VDIBc7XQ+0ucefoeiQisJWMlpm5enb148fzy8vLgt8c+GOdSirYsSGOGsSjRlZyh0zoQjMvG'
            b'HTYwa9wwDIS6KhyBCX6UnFGkb7v+uFvMant2KilXtuCchxCqqjhdnXCOKaW3b95tN+vzk9PS'
            b'uRASaWnKxu/bt+9u5o0iXTqnysoCpt3m3vuu6Uv99TefH9v9kydPPvrog/ns5HDoNutdimBN'
            b'OeaR8w/Y1jz6ru12hG4yYAryfr9//e7d1bubppkbvHKuTCHnyARKOCEkYyj4VpQMPtw99PvD'
            b'g1ImpZQxWGWQAChPBpXgE+chpDjTzlauwEIzxIsYOt9uDzFGQRLIgIzAhALIExELUAGyME6J'
            b'ppOFYsrgQyRSCoCFULESjTCZG2AKiFAap4QFQ0TGWH50MuWJR+NMWaAM7cDTqQg8+akfZ2lE'
            b'P+Bs3vvviQSQmZgMGjIKIYpQSIkEBUkx8hRBB0aJNmw0aY3akLHKAgEBTzuoCZv0g+ds+tJE'
            b'pDQwdMK43YX98S7yGCWEHHovVsPl5TkBxzTWZRHSuN2ukXDWlKtmpYSttbe3tzknThmJcogE'
            b'qJQNMSefogppSIyZSCtBW5QfvHhRNdXt3fX19bubmxshJ+TIVlaB1i4r7XM3RLh+9RpAi8Si'
            b'NGVlQFJR6MoY3XXHsnTL1fz09PTTTz4Tplev3l1fbb7++lvvszElokqJmYM2KufMIDFkL0lE'
            b'XFH96MefERZX767j2BcuWO2MLhXG6EefgxbNkK0FRZxSF7rB6MIY4wpyVjGzSM4cc87CCSZR'
            b'u9FDTGHcq5DLul4sZ8OhSzEAKnksFgIAEoZHdON7oOeEtoJHQBEzEymFBDDFjzyiuR8fiTCR'
            b'YIwibciAohwykFijefIOgghnZlZEejoBcWI9PPZwWmtFBh+7OgUAnIGzaASNCpTJCCiUNQpj'
            b'BpwCOCe1tFJGkVGgSLTGKTQYpoolFGHOOVMC5iSCAlPahSABUh7G7bypX715+dtvf3v38AYL'
            b'JCX74265aIyzwfc5RyFzHHb327tZ0UD2kNJqNvMpOqX7lEI/EJFRRmkjKRogJi05bh92QzEO'
            b'fZ7N6svLy6KqV6uVj7HzoR0ji+oi5z6UrvJj2m83h+3OM4FV/Zj2+wNvx5Pl7PRscbJcLs4u'
            b'9CeffmS0Oz09TYmbZnaqn66WT9b37W//6pu+C4i6cNaHDoCVUmPw1se6LpUujsdDHD2Aqqt5'
            b'TnezZsF5QtQVCK7v2xREKymWdr6s5/UJMx0PwzhErW1ZlqV1bdvGwCEEjdFoTaitLXKWGMe4'
            b'70yGCopJFzrZIkTylPxH8tdZE+8txQhAJERC0yRLk/qhCqePJkVaEWpBeI/imyz1CgAZRGll'
            b'lNbWIIqPYRy65HsiUtMJh1M104S85cfLMjEzyRQJLQhgyCAyKRJEFIoqJ9I5y/S4Q1II0xmp'
            b'FKlHE2PmjGmCSTx6E6dYjJxzJng/FAYAkZT4qK25uvlms31HJmUQ4ygxHrvDq7cj5ugKVTSm'
            b'aaoPP3w2LxcEsNuuFZn79UMYAzBESUopXRhCFISycfOq7I6H3XY7DL5tb9tuFpNU8/nNw3qz'
            b'3R77bggCtkIhZUtU9ti197vWj8kW1ceffnrsOnr3dru7j1pHrXrO6+NRz+fzk9Pz0s4f1uu3'
            b'b66Wn1wuaPWLX/xiHP/J4bCrqurk9LxwF1VdLOYrVDplc3Z6OV80d9c3X3zxRd92OeeT5Vyr'
            b'ojt2OSdFpbWmqQqFuZ6b8w+a+VlzefpEKXdzfX/97i4naRo3r2cieZ+6FHykoFVhtC5d0bcH'
            b'RIk5Q8KRfRfGxMlqHf0IIopoYsJkEMEMpKbuahKRMsJknf/hYfjDk/DRkIhaafNDSRFOPCsF'
            b'AE01m7htAiDCRGRdqRT6/e6RvM3ICIxMOQPFcRwFVOnLGKvkDD06n5UQImkSzEow42OYQE48'
            b'EZdJlCZNoIgUKUSM00GXhBQDKgLSgkpQOAEryQqUvL8QIQOi0gDYtoeqLp6XJ3f7NRisXF0U'
            b'xW67TiFV1onH2Xx+cXpRoF260/t3m5zCw92DMcYYJyIKcOx6sVoxNIvTDz980R0Pj7loioDw'
            b'0B6/+e470mq/3zNCTkykz1ZnhVskH/suckZCB6xCCIhorS6Kom6q+WzpyoIBdVlVDLQ/HvfH'
            b'8WGzPX7cMreg4uWz1WZ/c3pxmThWzSwGUGq5mK9CHCVnQ6oqyq493l5dI+Juu3n69KkxETEB'
            b'9wTFYt4UzkTsM0RbEOh4enFqCoqpz1niGGMai9L6IVldDP1YFU0ch1TYs8XJq1ffD2334bPn'
            b'htXy7HRzuxZmZ1T0AZPYwpExXnJSiIYk8sQwJkUMElJERcYYmph/P2A8ABgEmXVmYQRhQFFk'
            b'tFbmMReJjTJoMAkzZEzyw4Hkx5g4E+nECZWyhoP3Qw41ylxmoBgUC1EGiFmSj9ZRJumP7Th0'
            b'ktkQ42TDB1IAkiBJZpVYDCpFAACkCbWeKG9AkIGzQiWZJWdXVMeuPfZj3TTKaNAqMc6ai+uX'
            b'v/Fy/NEH54ljN3a77b7WLmXl92k7tP6QLk716dNzSZiYHx4ejDE559JCM5sRgh/G7L2rqsVi'
            b'NpvN5s1MBK+urqqqFuQQxpubm8SZiFLKQx8JNHfknjearPTksrNO+Rj2t9e2tKuqMFwTohLA'
            b'BGMYdTf63WGMAcpifmj733z+WwVqv9+++ODZ6NuyrK+vHjYPX3I2YbD83Bgt94ebt69fHdtD'
            b'd9gTgSIpSn08PFhrrTPCgUXVs6osi8OYy7JwhWHgvm+NVR9/8oEwbR7269tddxz9EKjUs6op'
            b'jC3LorDm9uodsizm8xjj6EcAAUWucD52U26SZEZErXRAyZOjkIVFkAiVAgQRmdTAGd+TZX+g'
            b'Zz9enKiQEFGTmvzIhGhQKUVAhCBJgInokY0FOefMgihESmlNRDElQE2QmEPOnpNjBGSNqIyz'
            b'5JAiKY2SOYy9xJRSstoAaRBGzYAOFSNmhSQiCpGASYBgSkHBR/oXP8IvH7GDWXxKCNaZktCg'
            b'0PPLi8uLk8ThzZtx3Q7c5vAAACAASURBVI+EpjINKuz7vh/a0VRhHq/vbrfbbdt2IXgUKY1p'
            b'6moxm0/GpElwdHd3573fb3chBG3NMHQpBdRkjfIh5CyFdRwwjPH2+t4ARR+MspqIjHR+OJmf'
            b'zmazYegHP2pNKXHfex087LYHrarf/72fP7t83nXD0PuHh41W9vTkEgBmTdwMLTC2h+Ou3J5d'
            b'zDbb+7dv345jr1CMJURYrGZ+GF3ptNacMxGAYmfMzDVVYQ2VzpQa7TiGsR/LYvbs8qlT1dt4'
            b'EwaJMVoD28N+HEPft/1wsNYiqvX6HhKcNnOGrBQaozkqSfxYGVMob5KJkD2VzjQUFZGJ7U5E'
            b'Ct7Dsd7rl6dO6H33rZSaFtrTPTYNjfARyJx5svdPZrppgmmLYnoPEpFWAJJy8jkOCkUUkUB/'
            b'6HRBWlBSyHFM48gpA0BIGZXSyioGNNNY5AesEdIjwo2njRROIzlkmRJ0JAvklEIIQRspnJGU'
            b'HekXlx+8eHHJEEMX3n5/E8JYNlVZVqCCUbQoS80JOKFko0hbk3MGyX4Ye5yi+SClvF5v4+iH'
            b'YcgxTfiTMYzzefP0xTNj1d3d3fphx5m0djnyzc2NhLSYzerKxRiBhBFcUa1OzuY5p5SMVSGl'
            b'tjvqu9tt343LRf38+Yc/Ofvp3fDw6tWrb7/5frtbbzabcQzCSinDGdq2tc4wdNvt+u7uJsRx'
            b'OZtpQ0VRXFycA8D05RB1COnQ7QpXLU6auqrm5aIqqxBCdxhyYFaMSo29PxzaYRiZsSxm3sfS'
            b'OqWwLIuUUt93+/2+KStbFkohgzjnSEASK60JIE14IRFSiiH/4MXD99CiiTbzN0vqb/44rX3+'
            b'JtkWEfFxXZ2BBXKSlFOI3vuUEiIqnAJ8lFIKHYCQJkaJHIcUlEIGTcRwdjInQgIeCGJ3OG66'
            b'sR8UoDEOlRHNzIzCIlnAsdZa2wnVhUg4mfonmpdCfFTJPlK4mDnlSMg5+O3DGgXjmBUrrdTl'
            b'ydNPXxw3D1ulbKlMNV9eXpycna3GcSytOQByDCKiBJIPu81mv9780HpOeZbMTIBKqZyz1WZW'
            b'N+enK+dcjHHsxqEPlXMB88H74P1yPlNKcUpEKvh0t954H5VSi8VitVopa8qy1q9fXZdFvZwb'
            b'YQOgL8qn8BGdnl5+9cXXwzikyE1TJZM3DxvII6d4f9cO4yGMXUyh16Ij1fPy6YundV1uNpv9'
            b'Zt8OffDDmL2hQjtbu7lTjUQ6bg+S6GRxmrNsHvbbzWEYBkSa0GoxZtRIhhAx+MAxmcIaZ4BE'
            b'WTPljjjn0IAQZhFg0FPw8g/wvcmz+v4zsWnpr1+O738LIoqFBEmQZBqMAYB6X14soAEzILFA'
            b'zmEchJMyjohyjimMaAxwTpEDZK/JazSSNVRgFAlYcpkjCjgFThNxSuOQpvmpZIZpss75UQGb'
            b'p5nbe04uiBCAmZjKk6ZwKi/ECVQpzHm33dzd3JpCXn3z2iAgQVEUv//Zr25vbrquC8NAKGfz'
            b'eeP0/mF/XN+HrlPCWuuUEufIKVqt22MfQgDACWVgrQMAFHDOieRhGN68em2MGfw4dQ5EZK2q'
            b'6sJocs5oq3jaNxm93uzu79ZVVaEyy1PGMXTdoLtjMkqNY/r8t1+FPhdFsd/vc+Ld7vDZZ5/9'
            b'4he/++zph+uH3f/xT//lm5dvD4edtlFptVqtUg4Tebosy6oqFosFEeWc9/1BkGer+XK5Kspa'
            b'k2u3YblcPj37YBj8erPZrNektHPlyeoMRRnjrHE555Tj6Ie+b3OOSpnVfJ7HdOiOxtnYey32'
            b'kYfNiALqcXatp8CFx5rgx1ivH+rs/1dSIhmSQgvvPflasgiyJERUYB4hgQhEyEorBPUDz/0x'
            b'nSDnnEOgR9FztEqSJTEoTqNIgWCQYxp7AiyMnVflvnCDgpxFchDRE2hLMgkFUYisgJWIBSSQ'
            b'BEIwpVYTwhSDgADIE0BgWigqSjd31ykFlfTdzYPRWiQ/f/78bFXMikYxdJklD9H3+3Dcb9ah'
            b'75+cnn700Sez2ez+/v7q5jpHJq20srvdrm27ieRjTSEiLKmuK63Ie9/fHqfzLGcJIRmKAFSW'
            b'jgiGMKQ8skRBbIfx0PUppVM56Yb29u5uGPx2u9ZGN+3Rx3A7Dv/mL//TX43jeHNzc3V1pVD/'
            b'8vf+4E/+mz+Z69U+dHdXmzSk77771jntjJo3S2s1KozJW2vX6+0Y4vF4vH9YH9peBCtXFGVd'
            b'lrVW5WI2//3f//3Ly/PNZvfnf/Hn65v1MI4ApFAPwSttBz/awgmj0toYUxRWRJrFfOs3Mafl'
            b'anXfX6MieCQUC+BEh1SchIV/6M2nPKaJrxcnDyipH67IaRiPZrpdMgvkPP1qoqHlCXxGwIAw'
            b'kZinf5iFkaOAQUQA5pyD98ASUWJSIdqUTE6acylsFFUcBkGlCzeryrKwhBJTDJyVsSSsRRQy'
            b'UgEZETWznoJQBHiin05bdWABBjRKZAqJTYhgjOrH8fs339rCxRy1KUefUOB4GNrdW4Sklcyq'
            b'0hW1cDhst34cmqr66MMP/u4f/u0nT5589+3L//Trv7i7uY852cKNduiwjyEP6LNF1EoBHI/H'
            b'wilj1bQFSCGGkMbRpyAIWqNm5n23JQJtMKa07fpjNyCic+bd9dvr26txDCkFbXS92WyCh6ZO'
            b'8wqH3j/cbxDU6enZ+fnTSs9GCId9G8aotY4xHvapCMaclPPZSVkXIY6H7nj17k7b7dvrt/v9'
            b'3hauLGo5dtbV82ZZufkf/q0/+gf/5X9NQADwy1/+6n+w9Z/+6Z8287lI2O+OfRe8j4vFgjMU'
            b'RfHRhy8Y8uFwcGWhjC60m6+ah5sH0gZCzikLMxAiIuccOJP+zy9BBfh47DOjmhbY06N+6uLl'
            b'sXMRERDmpJAEkTn89fGGjwPPCbo8vQZExBijlOKcQgClldKAKICJObAEyV6y/Tf/6v86Ho91'
            b'UX/88cfzphFkay0gtodOcVbMgiAkSmFWApS1aAEUUVMMIvDUaU1ND4GQTEnXzIyACraH9cvX'
            b'32ur2+3xZLnU1mmk4LMfWoTU1O7J09PLi+Vmc7fe3DCz02qa3yrA0rm6rKqqCiEMY1BKFa5i'
            b'w8Y455wpXGH0frdOUbtCIcKEqY0xM0vXbkBwXi8RJSTvnHVFiTnMDIHTCtHWtvVd3/eKqGka'
            b'ff+wZRaRcHt7O3Z9M6t+9tlnWuuT+Wp9u/n+9eunT5//+i/+4ssvvvj6qy8RIAVhTSlwzgCg'
            b'+y7c3jz4MEwa2rKYMwiCbepV4eq+C17n508+0GAPoW1sdTo/n89WCNT3w7t31ylLjFJW1Wa7'
            b'7/vhF7/4+er0BBGLohp6vzo/45Bu7x7KWR36qBCUVllkGkqxPDqep8P8h+vvceDOU2hYUkrB'
            b'+5TK99oEFCQRJmIFSqFCRAGe/p8JszEMfQh+ynEFwuNxP4zjcrVSSr199+b6+l1T1avlfFaV'
            b'RIBTXq8CRlmv12/fvr28ePL8+fNuGBigmc22h70g9H7UOZFWCnRMgQw57ZAEIYMkJK00KTsF'
            b'JILWekxJKRVCmBxHh8OBKQSO87PVcX+8fP4MWZCUKwqUWNTValFXtWn74/qLm5RHVFTPmqGN'
            b'tzc333/73e3t7Zdffr1er4H0ZrM5OT0vyxLJpJRQm9PT0+VyCTn5sY/Bw8iuMCJIpI2hGDgl'
            b'f3F+aUwZwlg1TT8c48GfPTkDTp4CCpRzC0CJAoEq56XebvdFUaBTwzCgZECGSoxxV1c3+323'
            b'vt+NQ/ji88+/+uqrw+HAzMIAoohGrQ5d6w/ttj94JqyaKuYMkhAEQMcgnEmXrq5n6+1+zKGx'
            b'812/+d/+9z/9sz/7syRw/fptUdbLqokhM0hV1UYXu91+u9mXZelD7obBmsJpW9UziPiwvSlQ'
            b'OTKgVYo5xUzaurKY6B3wPpZS3lONH3NW4W/sQ/6ztgsnqC1mAI2QEj4GdyHnLOGRXBCzwLRV'
            b'jJzboTfGkNHz1bJyhSC0Q+8KQ3bpSpclH9rj3/7Dv9vMFynxruuo7QDAFeVS6cxAwxByCjlg'
            b'REFlWGeOFvRkMUKYnhGTrYhEaOL0To2OUioDZE6iQUgSchZGQmtNUZWKHEHs/PFuu/NDG+NA'
            b'CqqiqMsaxHRd9x//439kkJT45ORE26Lv+7ZtjTHNrOq7sRuHruuKojCEKbHRVoDHIWhDWpu+'
            b'77uuL8uZcyWSlggxpwRslBKN56dnVOvu2HahY4YIkSQd+p0+Hjqttaqs1pizb9udH3oRFfq4'
            b'3x+v3971bb9aLOq6qpw9Hjtlipxxv2v7bjDOJPEAUM0qZILMiEorEgY/+KEbKlsrpUKK33z/'
            b'Xdt1/+e/+Of/7J/9s4l4MeG4QOjJs0s/xs1mo53pu/Af/sN/KsvSurJs6vncccgZoJzN3OxI'
            b'QTghKY2QJYQsrN5PGf66tn7gvz/SJR+PMaUUIU6XGiICZcgqTzIupTJMugcBAUCKKfs4hhRD'
            b'jFprUEQ+DL5fb3eIklIiZWxZMCcmSCAJxOecx1FEimZezOfBpwg48QdVUWSi+v/j6r16bNuy'
            b'NKFhpllum9gRx16bNzM7s8t0VXerSwiKekAtmld44g/wtxA8I4FASM0j0CXUiK4qUkVl5r15'
            b'3fEn/DbLTTcGDyvOyeyOt70jpGNi7rnG+Ox2K8x5OMWcFMWiYWtsNqUYLgjCS+0mSNbCWgp+'
            b'KEtfDpa1VouUosf+MOcRGWzlLBlDnHOc4ggUpmEf02BY2dmc45zFFlitt+c7N47z8Xjc7Xaf'
            b'f/llSqXv+2+/+8F7b5yb53kMMwAYQ5a48k23aqZpGIbesCWikgcRGKe5HwfnayFEZww4YBhj'
            b'cBILSYA0x5nR2MoiYtRs6rpWLSLFV37RaoIAKB4O9//in//HX/6XP5nG+d2bN19//dtpGrqu'
            b'6cekwqJ5UTooFGaGAnOYkxTrja88KOWY++PgyE5h3j3ane12N/vbt+/fn4ahbdubu9uqaWPI'
            b'94fDan2migDGGnt33yNo13rDPkUZp1j7CsiK6ups198epnHwbKz3ljHGGFJk/AON6EO5t5ZS'
            b'lhtruaY+wJCICiklRFVmlCLGipKIAiAZWmZ/KRhCmGNIORdQICRgY61GnkISKADgvRVi613d'
            b'NOyrfp5DyrWvvPffv3odY3G+IlcRkfeVkskxuqapVDKUmOasijmLZJGcUljQWmOMUEYxKLIo'
            b'pUQASoEFnWdrQEg5ppBLKiXnHAGlAKY5TePBea08nT961DRVKeVwOPWn8diPP/3y5//4F3+k'
            b'pfz2m29KKe2q0wKff/nFze39/f39uN8TERpOOfTDEZQe7Z5s15tlSDWGQwiquNnuiGzTrmzl'
            b'IYxhioWAGOeSXr1/O+cQYwYA4qW3CETE/NEf/7Lv90R5u91sVrWIoJK11V/+R//pH/3yTz95'
            b'+kXXdU1V/eY3/99//9/9t//z//K/kqm9YzbkvWvqKkkIIZxOJwABhqpyja+IaBzHFKbDPagW'
            b'Mni+O+eK/tEvf/7r3/5DCCmkOM2xrtswpx9/fKnIm812s9ntbw+M5mz7GAjfXL4/juHZs2eN'
            b'r9IwobHkPNpUFFRS0aIMCFCKGOSPB+vjjQUP0AEug++Sf4uIpSQmwiWxFAUAl2L5LJhySinF'
            b'lKeYpjAXUUQsWYGJrKvbBgCKZgCoa8/GuMr7tkM2Y0gpj7WPXbderTdV1TLZKIKKhFQZQ75R'
            b'LRUCWjOPx2maiuSQo4m8kOUqViQTuI+T4gL5llJEIRcAZmOMU9NUNYNOY5+nxAp15SpvQOau'
            b'bXdn3XrTisjp2DMaIhtz8L5+/ulnta9O03x5eRlSrmz99NknP/tHw9dffx2uY1VVxhgVmefJ'
            b'sC+KMZVcFJBDzIdjL6JPLi5+9tNfrs92xtqXb17++rf/MJz2VeusNdM8hZRU0Bgzq56GAQCM'
            b'Mfxf/zf/1Wa7urjYPnm6W6/qUtI4TuMwtb57+vSTZ08+2W63a7/a7Fa3t1evX70y7F3lVVWk'
            b'0OLDMlhXXrUwo7eubqraeEDVWGKYRXWzXZPB2/u7r7/55nfffns89SmlEPLSalsK5CLMtmvX'
            b'Z5vzMAdQUsWqaQD55u7usD8Ytm3VLt4QBJzmaZpnRTDOacqLKPhj5Ql94G2Wqesjzr7Yp5eE'
            b'd8NoDC221wUlCmGewjTN8ximaQ4hJQFApkW8DohsrPMVMrOxrq6qqmFr2HhmykVCTrloVu3W'
            b'Z67uiG0WLYDAZhFVFJVlPRXVVEIpKeUYU6isI+Kl02GhxIkNGRbAogpoikKMRQkBuWg49u9u'
            b'by+n0wRFQMUQGpYUB0PFO0LM/fF0OJ7CXEAMAIPi2fnZdrPr1t3Zbuec64dxSS24vb2NMdZ1'
            b'DQAhhKLCZFLUYRz74xBjCGEahgGI1qvtZ19+9dnnn3/185+5yr27ubw73LMldkYIM2ABUKJc'
            b'ZI5JAMgY/hf/2T8x1liLMY6H/d3t7c311fXV1e3bV+9z1vVqSwAvXv74b//t//Wrv/ub129e'
            b'rzdnxvqUwjj2OScA9d6sNh0RIkgpRUoiJEQtKU/z9OrVizmGw2H/+t2bu/u7+/3h8up6DqFq'
            b'2pSL9bX3dVW1KhhjvthdrLutMbZq2/PHj4jtu3dvh2E8Oztr23azWndNU1Ie5iFLAXqI8Df4'
            b'0GT5oI6H5WCh6gOL/HC2EBFgqWc1y2uAUkrOKeXQT/08hTmlmFIqUlSIjXWO2RpjEXHJNgYi'
            b'Y12z7hbvj3UVGU65zDEAEFkbUiFr2Xk0xliHbBCJDC/DoIIgATMSk4BIzgaZkYw11tqF4V7C'
            b'1nMRQCJjC8CUsggKYIx9P17t7y/TFA2RQfTGMKZpOs3zYZ5PQ38ah2GeYilkuKqr7tgfU87W'
            b'2IsnT54+ey4KL1+9+va7725ur0/9yTA1bV1V3jpDCCHkec6nfpzDXLSolMWhEkKY5phSAeLj'
            b'6fT28n0/D4I6hHkJE1sUm0jkm8Z5D4hcX5ihP93e3X73u9/98MP3fd+DMha6vT2+ef3++urm'
            b'9atX//p/+9f/4//0P/zu26/Z2oVTKiXnnES0lCKiBNTUTUoyTmOYI4ASm5TDNM2E/P7y8vXL'
            b'V/vTnkCub6/ev33TrVoVreuqabqhn5zzXbs6HE7TMIeQ2rZD5ru7u34YNuvNTz7/8vmzT+7v'
            b'7i3bknUYhhCjYWKkHBMVXYRNC9S0HJhlDFdVAV1ENQ+sL4AhYABmXsTyqeSY4pzSOM2xSFIt'
            b'CBlAmckath5Ul7B8NGwsG2fadXd+cXE87a13TdeQ4WkahnFkQ6tuPcZU1ZX1bskuISJirKrq'
            b'oUCTwVhbtbWrPTMLagmJCJ2z1lq2vIheFbGoIhtjXQaYU8ogRSWmkUze7+9Ox1OKMadoDDlL'
            b'oplwyfgLIeaYSASqqttszwjodH+8P+6ZiRkPx7tXr394//6NMWgMrlbNbrt+tNvtthtUOO4P'
            b'RSjGDCpsiK2pmkpUb+/uTv14eXN1eX354s3Ld+/fpJIA9dgfUxEyRpFyEev8Zr01bMd5ZvHx'
            b'6v3VuzdvD/dHw7ap1ljMPJW6as+25ze3d9999/3l9fthHIA0FymF+n6MMRnjSE2ci2QsQmEW'
            b'JOtsQ2wAKUueYhzHWTJLBsPkPec05jI1tfXenO/O1l0b5zT2Y46lruquWY1zGMYQo8zzCIoX'
            b'2+3F2c4Zk2OxpjK2zlljzJBLHKc0DxUxgkrOIsVaYwyLFFFBRmfNUmhjDCOjoiooE1LOBrGk'
            b'VEqxzhWA0zgeh3E/TK7tbNNGALCm2WyrrhNQAHGOfeXYkjKYyvrKKIn3rlu11nJMIcyzihgk'
            b'gWIrkyVO84isq3VXNQ6IFHROc9U2p75Hx2DsEELVtd75GOM0nIipW7WIAEhVXS9DgiDGHNkb'
            b'IU2SXWWyxnEcXr9+k1NmRsVCVFJJbKyCc35T1MXEaLyx1ZKXufJtmML333/7m9/+w/c/fPP3'
            b'v/7by6vXT5/vPvnk4idfPn/65HzTVpumtgAQY+18fiAmQVTmMKWcwZD1jh1bZ95dvj3s75Gg'
            b'Px3DFIwxUwpFJcwzqLZNw8akVECBd883MaS6qj/77NPHj58xOW/qi/PH//Jf/uf/6l/9F3/5'
            b'n/zlp599Oofp6vo9kDZtM45RRVWhZJW8VA8RLPrIpdMWtICqQEjzHKJBb9l6bwDSMB7nqa9q'
            b'8+hid7Y7F4FpjDkLKKoiETtfDeMsCjkFRl21XVPXTExgFKmum8UFkGPIYYYQVDIB/aEWfpnf'
            b'icgQP6zrDw+9pU+EPLEzZmnQKQj9OOyP/ZxTu9pkBCBqurbqVsoITFVdlxQMIy6t9Iacs2wZ'
            b'ANgwqEpJmjOIECigqpSmrY1lVlCQpUcHVa01y95gnS2oxnDbtWTMerW2uHhDgA0b65zzzntj'
            b'XUy5gBRVZQo5p5LZcCrxxYsf3r1/A6DWM0BGRpUCwE2z3e2eNM06JB3GOYSoCNba/d0RAAvm'
            b'mONh2L+/fps1PHq6e/T4YnO27tqqrpv1auOtzamkLM16A8wiJaUUUlQAAZnnWUCRIKW46EyL'
            b'FFTo52nKUQG9r6wzpZQ5hGma+743iCxFEXm93j59+li0kGDbrv7iL/7iH//yj7WAdfztd7+t'
            b'G384DH1/muYMygAkIloIAFkxZymzqgoXEkyCSiRJcslauBDRHEM8JIFgDNRd5SqPiPM8zymy'
            b's4rYj2NR3G6984ZZtZSHB3eORUAVja2995bNaM3DJI4sRcggAC4NNn/IPf/hkqgfi75VkRA+'
            b'PBlDSn3fT/PAzm42qzEFRSACa9ksZYIEVVWZxWEGD/2/C4m22e2kFM2JjNu0XUl5nucQgkf0'
            b'xhAwKFEqSBE8G0Iy3PdT27ZhmGLO3Fan0wlqt9nuPJm+71MWNo6tKaWgfSh5kiJLmxIiMltC'
            b'3u/vp2mqvHkgprJoUZCcU3LOeV/h7d08RdGsKIbYkE8kwqYIRskRoGIOin1OZRjynI3yo23T'
            b'XTxeBd0HkQSr1coYo6r91JdSLLiF3S9FgY0oxFR80zS+yvs7JFFDdbeylvu+BxGzrEW7T86Y'
            b'ERClFGOp61aWzTCMABhDunx/9fr1q6ury8PxPuc4z9MUAgBaZ5u6NpZLyUvHWkxpUaFIyXlp'
            b'i5LFtUACRUoIeVZJgpJTPJzGw/3x/dXtOAQmu2QAl1yQqW3qtq3btumapnImxjTNk4jUzapt'
            b'OySchyGOQw5zyVE/SBsWvOrjdQUABLhQNMsyiB9KeBiRlkWPKZV8GgcFWG82dVt7Z5E4l2gM'
            b'rlatszbNs7fG0Ick6rIkjIiKsEKag6RICpbYEoEIZCHV2jrH1hF564gYSpGSN6t1SYEZUZVI'
            b'iTGnmGKovbfWFBW2brPdWutzUWIGImSTAchwAUBmX9W5pLfvXp5OdwiiJYd5ECklFxHISStf'
            b'xVj6Uw8ITdsCaD+OTdsV0gylMIABMGRr7+pGAC9v777/4eXV9S2yZ1edxun+0L+/vrXGtW1b'
            b'Stkf93MM1lrrfV037AwgF5BcdHt29vmXX3ab7WmYQ0pV1VS+SjEv/VzzFIxhx96K5Pv7Qy7x'
            b'dBpq53PO0xTCnD7/7LNHj87/2T/787ZzP/z4u5evXv346q2z9fnu0W6zG07jq1dv++NASIBi'
            b'jGnrGkhTiqnEIiIAIpmtQUOgCgzIFFIJw37s4zwDgi/CoCblnEuBIzrnnK9XbVc5g1LGcVbg'
            b'qnJd11S1j3NkZni4sRA/CBCUHiISPoKlsWRZ5h4RMgQIC3WthtSQMCqBILAxjTPr9UpViNkg'
            b'MTpnDEhJMY7TaRZ0bERknueUEhE5by2b+35CAEMo3oPLlhhTsYqdrZrF11PAA2DROc5hGEqI'
            b'4zjsT8e6rZjZOF6v16fjNMdQ+6qqWwBUQIFlHCQFBELSxQdL8JCSBU1VO2ulxFxSTmIsSRaR'
            b'6J3Z3x+XTfLLL786O9/u9/cv3726Pu1d7chSVgkxTikkAnM8UV2Nw3R5OOapBLXX+7HEMoZ5'
            b'CoF5IAYkNcZgRFUEpSxgFNFYZ1nnZF21O3908ezTw1zKzTWAZ9M1LcpDfP7JWOsAS13XznNK'
            b'0/X19dNHjz/77IuffvXzX/ziFz/76U+/fPq5Qvl3nz//P/5PPPaHizDtzh5/+ulnXbN69+ry'
            b'+vq6P0opxVpb1/V6vTaGxnkahn4KQiAJtKpd3RhV7yvabFd1XZeM/+/f/YMxkiOGEBBkUU6K'
            b'5L7fO4uNY/ItMTFD5ardxXnXNdZyjrgIA2fCjzj7R80xfFCQfvyWfAhseHgJi1OVCoKUIqrG'
            b'WURYZPXzPANTU/uc8+tXb+/vDzlnKuitJ6KFDHZsvHfOWkNskbxhNSFb69gwEqNmKWMIIYRc'
            b'tOlatn4Kc8iJ2J7m/ubutl23iOhr99VXXx2Ph65pPCh7L6WMMSmbylZKmHJhIZWHpqAFT0k5'
            b'IikRwUOH64OyNKVS0izlIIDb7faTTz776mc/OZ0Om4vd1y++H+M0hSCYkF3lWLRc3eyBDQKz'
            b'a0MY317f3d4Pbd2eddvdxfl4PN3e3oaUyLBxtoikMFNJXmvrXN02xGUK5djPZ49Wn37+s6zu'
            b'dDoOYxZlIiKGttkYAJqniZk3m5X3NqXw+PHTP/3TP/2zf/JPnz17tlmvAeAQ7t+/f7s08z5+'
            b'fPHpF58/e/zsdOjH6ZhKZEvL3fEhrHExxBXDbK2tHTVd6zwaW59frD/77JOm6WLMP3z/di9D'
            b'jhk+RA4ZY5qmQpVxPBEkKbFtGiRdqoEBJcYYYyQi7z2hkQKMLCUtsRl/yC8vBx0R9UPs+zKB'
            b'ZSkxI1tYyuoEFA2rSgihbisiUCkpTMfj8f27N/v7IyMasd5Xls0CtwpJzkVhjgoGMNBSGfZB'
            b'l8AocbbWLuz15mxXd22SkqR0qw2rPDnfkTHH6cRMMYYljz+p1t5zkSwqgMBmDqkAAIsiICEq'
            b'LOFxKSVdPD1kSog5Z9Xlh3iaYxZUASZzOg4x5NVq9fkXX0SDb6/f3d5exyzWG1f7lMLhcP/u'
            b'/V3tPSgVNNMc0KCshgAAIABJREFU+yEiV0+7zng57O+O/fEho8eYVJboOsVUlEpnPRm429+/'
            b'ePVK2IdAbFbWgzEkkk/jYZ57QDE552EYp3kAyE3r69p3XVfXdd/3fd+Pw/APdzd/87f/97/5'
            b'N//7/f7aOLN+dH52vnW1u3+xf3v5dpoHYwyzkawppb7vVcs4j7lE733T1d12AwxFZmZcr7e7'
            b'3QUAnI731ngpg4h657z3OWfnXNPUBFhS6E+HxUpPZHKJIU4iKGWOcxEozMuh+feKnz9StvoB'
            b'KdUPavGPl5aIDHlGawgf2GhmzllijCEEa23KYb8/HA73lni77koSKrwk0hCRBWIiLaWkVBsH'
            b'qlAK5kKoyAoMSgClOO+qtrPOXTx+vDk7F8YicnO4t2w+/fyzmAPdQbdeq+SqqhSwiLAx7CjN'
            b'iYhE9TQOVd3wB5aTUBVx+cAsno6cci4yhrjUWFrjE0VCjiXfH08/vnxpKnNxsTO1XbXtrlwA'
            b'wP3h7jQcU0quqrpu2x+OfZxVgZRVuGgRRWKO85xKVBTjrICWSZHBOK9AyBRzASImOg1T0ZvV'
            b'2dPjAHW9ffb08935NpXw7Xe//f77b+YQzZIHl/J8Op18ZZj55ubmV7/61be/+z5nGU79+8u3'
            b'Oc8ppxgzGW6a9nQ6gWCMcZ5nY0ztm/40MZlFFf7wS80qUHzjV9uVQIkJFZICGOsl6/E4pJSt'
            b'9VXFxhgtAvLQ0lxV/hSmFGNT+c2q7cd5v7+/ur5fdbuL88cENqe03+/HcfTexzARszxoxhd9'
            b'pyDh8p+CTPTB3YqIqpJTBID746Hxrm1bAJjnGZmsc7CYQSQBACN565yxmbImNEqYBQmQ0BL5'
            b'2rvOVNbFaV43NYi2TdMfjqvVqq79PPVNV1vrC2jlfO0tWjeG+Xx79uz581hiKvHxxSMgJAJn'
            b'LBMx2xDCUleBzEmS9zamwJUlxKapxhiGYbTeicjV7Q0Zs7TxNG2bU4q5ACRkM4UCgLWvD4fD'
            b'r37190SgRqYcVmdba22ZcxxznjOKsdai8OFwQOR1tzLGOoYwxd/85jdUoqZkvd2eb7v16uZu'
            b'f3V1I4rb3flpGOY53N3dsfW+anzVlKIp4qeff/bn//RPfvrTn8xhaJr2cH988+aVMcYQgfPc'
            b'ddVms6kqJyLjMH/z9fcvX74E0c12tdutm6Zhc+4qO44zG3f17odvv/72dBqYbIplEXUsWQNA'
            b'UDe+XVfWsvf+q6++qho/jMfLy3fTFH744cU8zu/eXscgCGyNZTTLrZNznqZpnucSU+V9VVVL'
            b'3IorZKzdbDbAlOakIsZZskY1i4iU/Hsrzh/I/fSDT1UfIrsf7jNrraoKQiyZFqkg00Lm55zl'
            b'wfGli6CAHIGCFgVRKSWLWiRSa5AMkqvq2leG2bHRtl34yqKCiN1m3bQts8mgMYRcymq1Imcx'
            b'sSIULUkKEVTO0Ud6HOCjDXLROxCRgMYYUkoKJcb5NJ4AIJUyhjllIWM8G1WUQvMYl5DDVPLx'
            b'lOY0xTRnCexs3/d128QY8xgUkcVgAw59xXUIIU6xqmgRWtTOdo0Xq9b6btOcne/I2aIyh+Rq'
            b'50oOKaVSgGGZdJnt5myzXm+cq1Iqp9MwnEZCs93ujDFmqRFSVefcZrPZrFbbzQ6AXr9+Q4Sr'
            b'bmOMbZqm65pxHipbOVMPx8v9/mRNbYyTkI0x/dw3Xeu9izmENEuWlW3rtmrb9tGTizlsSkm3'
            b'N1ff/e676/e34xA0O0Jr2WqWnLKIpFIk5apqRAqAHYZJkmQFa6qu60TkeDzOp1Bb83GQyjnT'
            b'w0SOH39BHx9/AA+r4gPV85DJpqpSCiwrHjDZyrm60lwQCyISGjaOgK3x6EC5QJIcllz3kjCn'
            b'lBiwreqq9saQty6EQNZMIUxRfG0LQQEVRgWdS3G+vuhatlagKCEyFC0yT4jqnDPGLmSLQUAp'
            b'qEVVi+RclCNFVJCYAclQSLHv+ynFOeaYSgE0pmLAGHPKKcSsYJi5ZEllDmUWiWxo6kdJOQ4z'
            b'WSOppJKxKCsaayvj5zHEOdVVtQhu/bp5+vxRmIeYM1glo642vnZRCtGDn2r+oGgtRZEuv/jJ'
            b'EwK4ubq+ev/m8urt6xc/1t4+vvjCAEBZksFVvfdnZ2ePLy4uzh+v19uXL1+lEIno+vq6lG23'
            b'qg+HE5hKdCR0Z9tH0zCHcY5zMkYAqKgoCjuWTCLFVW673Zz6Q91WxPjo0ZPK+5vr/WKAbKvK'
            b'2YaUxzjmLIRKQFoAREHQkA0hlFgEgSmTrUqOUyhpjLTeuCXZRxWJHjI5EH+vYkBExJwzADzU'
            b'+H6IHBKRGKMu/ahEywXmva/rOk4zAORUVNEYt3wLRNmS5lL8Q2+FAATJEsQ5h4bjXDLoOA1V'
            b'VQUtqoWAUXIfpjwsDZy+W682Z2fLbgiYrfWk2YQguDxzDZN5uLEApCRVlVREJSUqzCnPYKyx'
            b'fhhOVzeX76+uRaJCsYaRTBZJRUIuSUG1JCmaRTC7ym+355vt6ubd5TxOkotlh2hLKTJrtqWt'
            b'OtNwnEMqGUVzSQBQVbZZVVnHfuj7d+Nh6EVgf+ynOYSUrfG2cgIQcw4hDsM0zeX80aFub8f5'
            b'/vLy3c3V21zC2W716PGZIQLr2Nhqte622/Vq3dZ1ba3NOd/e3g6nsW3rcToZY+rGd+1GEg4h'
            b'nG0uGr/+4dsfhsPobMUGm7YFkGmaqs7tLs7IYt149qiqN1e3xtL5+W79tH1z9q6tO1DnuXHW'
            b'S0YQ1ALGWWcNIsSYiMi7unYOkYvq6TTGfLfdPLLW+s6t12uYZyISROfcPCVBXHrnF6RhURw/'
            b'DPWLWX3howUWrno5gh/R1CV2ORUZ5xBCIgJkw8xkXCnFOrs8WX3KJaYSE+RcRPscyow5xwZK'
            b'yIFtg1R5Q8M0GFOjc+itq+q66cDY4zgtUzkAACEDMzOp8rJJq8BiywBgIgVgAus8MJE1OcYM'
            b'RUu8ur169fbVu/eXxqL31jsTOaMCKBrrMUBRFSkpJ8BoqW5XzcXFBQvcvr8ZhmH5wNiiRMYY'
            b'55wDtnVdwzSUkmKayRJZGsI45XmY+nEcx3kyxk5TmmM+DuPZ9ty5phjJWZZ0P0N4PN5stq0p'
            b'PE/3OffGEEI6HW+Nc1Yhp5QXm9Hy1LDWVlWFiKfTyTlTV+0yeK23Z0U5l2JNQ7VX5VKwco4Z'
            b'd7td29VKkjWgAWQRyP14ujh/dnN9N4yn0+m4atpxnBCsCBTQIClHjTFL1sIFChEzo4kxpTke'
            b'QrDW1lWzADZ1Xbuqc2xXTXO6uSml5FJgmYZUH+Yb0I+b4B/OW/DgmF/EysL8e2HgYq+IMZay'
            b'cCdqbcVsF0NOEVFSNvhQlZhLiUlS0lwcsQIoSySFygYU9ka9Wa2qtmt90xnr0Xm0JqmUkKqq'
            b'AmJkAkUkcs4vxICkvOxZD3wnIhIJAjInKUgLSqeiue+Px+MRABS5FB3GWUpCRGe8s1VeukCZ'
            b'CFmBBCDJUuyyaM4QRZHZsjPOVrYKISmKiCCTqqLBtm2q1prKNKZbpRkdtVXrfW1c4HHe359K'
            b'WRCPNE3TOE5Mtl0BcU6lVyRfwfaszWWehv043JqUQwjTHIbjke/v7+vGe+Mr3xhjf/6zXxj0'
            b'49SL6DBM+/2+ub2zbk1kjrenYRjub+8lyzhOzPTlavPHf/KLdl29u3rdT6eqtcZgKaCq0zBc'
            b'vnv37vUbAjydhhJLipIBVKIW1KIGCQrkWAqXqlnPIU1TGIZT5bx75p1zm82W2TZNU7vKMT/Y'
            b'oTSD5o9D1fL1kTE0H8w5H98XUC0CIIYQiiiW8iAPxFIUka311vqqqkQREdlYJkwQhUEWnG4p'
            b'GXOGFAgxTDO7ShFd5aeUHDOgPnn6mBCVrBhKIBLnylbOuSxl2UVyzoiwkHE5Z8OMICAKS1qg'
            b'EgASiJQ8hcmwphQLkAiM0xBjNN4hk6hmiTlmRERgNqIICIiEjJwLpJTGcTgejzEEItM0nbVW'
            b'AEV0YbaKlHEeUkrEoKSVr7t1S5YFhQwax1VTbbeb1Woz9PN+3x/2fS5RZgghpTnMw2itzyl4'
            b'C+Nw13b1J5+c1/7p9fW7d29fT9Nk7u7viySAIiIhhP39scQy9FPXbX720584a3/1q7+LMfja'
            b'TWHuhynL/dnuYuj7/f1xvV6fnW9ijMxYte7J88fnj7e+YVPRl199AaDv3rz7/puXBFpSvrq6'
            b'mcbgXOW4zphTAhUlIGM9E4gUhaxIArioloCcsmPbGizOVapqma1hBkUQwwjWLuDnRzUf/vtG'
            b'nCVNefG6LMAtqEKRAoBAAABMig/poUsqBDMb6+McUk4gytawZwFQhVwEiiDI4tyf5nkI01I4'
            b'4Nsu9CeqKjIsYHLKzkHtmoVoVw228jlnsuYBeFMlMgAp58xdzQ/mehGRJUEkS/Gt1yKSckop'
            b'Fk1SDsdjPwwJgC1Zg0RkK2vQOFcZZ21OqioaS5ymOEJStmTQt8b7uvU1MHMIIZW0BIm1XTel'
            b'CYXYsUAhIgEap/k43iWdT/tTKdq1q50/r6Wa5xjyhBMyZQUkh2SBSJgxpZA0nJ+f/8mf/Omj'
            b'Rxff/PbXwzCJ3hlbW43F+zoXffXqXWWrn//kZ7uzi7quSynffvu7lKKihJyQ7RwGIDhM+5CD'
            b'W3N7XnlnTALv7dur71+/e2yrL42lTbd5+vhZ167PurPrF5evpuFwe6sxt9VKCo5zAbW+rgjN'
            b'qlmJ5tvrm3keN+tVt14djkfftuzrp2fndbVq66ZpOu9ryyZNYby7d4ZKmBeZXoxRkjzMUQBL'
            b'tgzxMssrImjJ+qEbjAl5magApJSIAMJFpSAo01yC76rKunkM/XBkQM+ESWMsgJhVAcA751wl'
            b'IjGFlGV7diEiwADGrLdnMUZiJ2qc9WEOKuPFxYVz9TwOYY6WSVI2xOR8yqEUMWQFciixqh0j'
            b'acpS8hJAA1LCNGDJ/SnWm9U8Dy9ev0JrL549ub8/AKlokBIBlRgEIasIZl+T9ZwS6wHCDJqt'
            b'ZD8VMaTGGGEURrCIltAqkLbrFkdIOVjn69pDwcN9H+SIVmzla2MKiKCsNk0upW7dNIybtZcC'
            b'kIqrzTzOMYck2rpNt7o4333x+NHTFz9c9wPe3QczzsN6vT4/20GRklPXrR8/evrJJ59U3v71'
            b'X//17779epwHRIRMdduA5TkkZmIGhZLLjJkBCrHZdGvRNPTHEFKcU1O9fPz4MRQ9Oztv6g6V'
            b'Q5hNKUCO0ABzynm1atdnazYIIOPoK2+N4/PH51VTV1XjrK/rlbfVPMWbq1st8uTi0dmqayu/'
            b'z7GyLtMEQB8upAXH+gOgQRbsAEGXOGtFAUEEWTZEVFBMFFKyKZFhtiZLCSHENOvS0F4kp1xE'
            b'kWjRpJMxKlBKUcV2vfHehzCVUmIuD89O61NU580SW5piQdLFE2GZRCSVD6ecmZkVGUAKFAZC'
            b'RDZIBFpUS1FAY4zJeRiG/WkfYiRDbE0uiqJAig/P5iV0ktu2TeU4hwGgVLUhZFXuT5MxGaEY'
            b'Y4xb0gYklTgM8iFYLuecFcBaWZJRva3RSFVV3vv1etO2bWWrnKXruhj38zynlKWQc05EFOHF'
            b'ixc/+ern1tSn43Rz/fXf/e3fX76/MtYbY3i16s7OtjnEcRhyzqf+cDy1L17e/z9/8+9evvxx'
            b'c7atqgqZ21W33x9N46y13plSEguUEAEkM/uda+vu+ZPnoHh7e/viux8v37yv69bZFds1UJ0k'
            b'akHDCITL1B3yPMWTE2sddVwxQZZ5HOcxUNuuznePvVt7j5atd5tVu15VTVvVbeXD0M9zCHM2'
            b'xoWY/gOi8AOCBUQLyfbwZlZlxcXpv4xctMyiy8FijjFKTotVetkfY4zARkUeQAwtOWcEqKxz'
            b'1hnizJxzjnNYYIuqqkoowFTZh0HQLEp5ACUsIpoTABADG8NIQFooGXyIS114glTyOM9JC9U+'
            b'iQQpRTM7pgjzPKeiSIs4bGEV0BQlAmc5CxOSMWwJNGqOJWkEyEUiZXLgvfeGbc55nsc5zYs+'
            b'2xjDzARMwIgao0oqmmMOqpks+aZqx2FyxleulgTOeOMdAEnWaRiJ7Tj0tzdvX750YU7H/Y2W'
            b'CMSmaRpVHYZh+STd7u+//uabm5ubt2/f3t/fL5qFx0+fbjYbtobozenQW8K6blVLLlESGGNr'
            b'W1XG71bbT559kpPcXd+9/PHNNIzWV02ze/d+P82AZF1V+bpGZBFh5hCmu/srAHXEXdd5a6aQ'
            b'd+fdHGfrtFv5pjUI2K2252cX23YznEZNuW1XS+53CnndNQlH+A8B92VP5I/vf5Q/qCIaBlUU'
            b'WZLO9EOM7HKSSD4GfmosOeTUOB9TyjmnlLBoSsl73zRN3/fGmEVjAEXAQmWdM3aaRhEBYgAo'
            b'khzVZEwIwYP7vbqVjXVLLpcYYiJB0SKiCoiaUgohZBAkEEtVW228mTDfnPansVdcouFQl2Bn'
            b'yKQRAKUUttR0K+d4PI3HchJl62pjQXMqRWKJHqwxdvk0laTee++dc5XzxloLADlLjDKF8SM+'
            b'cHt133WdKqqiN1VBkAKIXIoikOTk6+p0un/98oeSYlVVdcUX5+uYZkNE8zyXHL33DjnG+XQ6'
            b'dV23uzj7Gf10CmPOebVunz57DACWza///tco6r011udsuKHNZrNareq6TiF/+81311e3333z'
            b'3dvL9zlkITOGF7f7/jgGtrbqVtvt2nm7jNnHw/3UD/McQtKmcVXd1J1LMhtfee+JZekXXWyT'
            b'bw9vLZvKeEkZinjvc5UeMHeVxTqh9HuT6sM5e3hKfrgSPkCpSxjzR9lJ+fBlyBBzSSIpLyDY'
            b'sk2CFpUMiqgPSZNhGpcwjco60GIJrXnYQGOcARwAYEEPQIQxp2YRoJJjRmPtQ3ogLNctlZJz'
            b'EgJE0qIKhM47cAYtkeN56m/3N8f+sPxzRAEUEOkhOZMAgUuJZNSxWbUVFjnaPhYhLMYbMFZC'
            b'KppjiWiwgCYpS8baQj94axlYRHIspEazkQyqGnLI8/3YB2Z2zhkiUkTmMKcwzobI1dXpdEKE'
            b'/lS9h8zMhqHrWLU2VVU55+hhgUIAMMasVqvd+fZBNZGSMWaapmmaxnFcbzot0DSVcy6EyRhz'
            b'dna22WzCPL/48dXf/e2v3rx51/ejNc6gGWN/GHMUZWuqxtetb1bOOaMg/fFERqrOIkp/7I+n'
            b'fVP7zdl2OPSu8oRmGCZL/apzw/3tzdU3Ty6efPH8c0N8fX39/v17VGh8NU+DQVLQxful8vtI'
            b'I334go+Y1sMx0t/zcQCAi+l+gemLgDO/F0QAENHyZHzoJPkQArioDBZ03hiTcjDMRFRSqGuP'
            b'igsWuJBMS9GOfkxuNoYIgRZolEtJFh7ClQF00TAaS2wteJsl3+5vf/fDt9+8+jGpGMc6Z9Ul'
            b'vY0W3+QCOgJASPtpit3atJ3vVvUxpZTHxm7J18bZGKMi6JIGvmiKVOc55JxxGVMVS9EiCIBV'
            b'VVtrp2EIcZqmiZk1l7Zdde1qtdoM/fTmzTvJRQEQMkIueepPCQDONm1T+5yi6Zp2t9sVSYfD'
            b'QXMpIPfHw4vXr/an/c3NjfV+u9tZa2OMx+Px1atXjW9EpGo8GS6zxHnaHw9TmEHwcDhcvr/d'
            b'7w+I3LZWQFIR8twYtpbqrt6ctXXnUgrDcLo73MQ5WDbGuKWaYJ5jE/Xpky+QCICkYJghzPdl'
            b'lpzhyaOn1pjT/nB7c3M6HFNKBFJKXiygoLKo+hAR5AEvBXiIxFpOEhESIpQPT0Z6EKCq6hKY'
            b'm3NOSGDMwlLzgsozLfjTcha990tv2LI1W0YmyKJL3kzOuVuvUkrWG+/dEiuCzpA1SYSZkbCA'
            b'oiAgGAJi1kCMi4EetSRVVSiiGsPMVucUbu9vb+5vQwqm8lwyswIIcFEUJYHCSMoGvavCoYQ4'
            b'lOycsYYLYBLFkKaqa60zglpKEVQybL2b5/kDIksikGJGZBEwZAzZ2tdNUxkALQkADELXNVXl'
            b'K292Zytv3fXV1ZRjTnndNb4y3iJAASx13dUO78feMHPTNCGEUu5ABADeX12+fv266zpm3G63'
            b'jx49ssY5b1T1u+++e/f2kpkXfX8/jeM4HoceAC7OHw9zEEZbV5oxpsJMpvIaB/badO32rDk7'
            b'75zn436Oacg5HPu9IXe2uVivNqpsXaNicrTDOBnjVqtNmOJ4Gp9cPPvnf/YLz3Tz/v371288'
            b'w3rVTv1+GgbGAqhQfh+O9YfD1gKWfhyzAJYnoNJinX6AHx6ib5ezuDCJReTjZFZV1XIFLuTj'
            b'MpcsN9A8zw/6wZw/3gHLn7v8HUIIIQTVqoiwCC5RSqCLtIGXIHpjnLMECKJRSy5lqSCZ8lxX'
            b'GHMUKN26fV5TJnh7ecNGFIpiUtDyEL+bRRIxIymSiKSUS0yTgrBxx6EnZ6uqUoCcCmE2RAtS'
            b'U/lmoe8sMT/Azrpedzhj3fi69pLDPBsi8pX99LPn8xT743A8HsYhjGOvqsaQiDS+2mzXKYVx'
            b'OGiJTNYaNKdTP88/EFEIKYSAiHXdbjZmu92enZ2JyM3NleRSVdX97e393UGwNF173+8P47Gu'
            b'6yQlhrLb7VxbP3r+/Prq9rvvvh/nyMyOuWvqiw0IZV9r1YLzqhBC7mMOYxjruka1oLzdXjBV'
            b'aU7jUO7ujj++eBOmICKNb/7qr/7qz//sL/I83Vxe5yirtpv7Q5gGZymRZC2EuES6L5tzSbkA'
            b'IOLHfRgeApUZiHAp5Pmg9F20ymzBGDMMg4h0XXM8Hgl4s9mMw7BEzUwhrNfr/nCcwri7OCOi'
            b'fhhimB4UOCLr9aqu66UgMaVU13VRIcPG8TiOnWkF1FgLhA/lJiopllJYrPFIqiiIyESGyyJT'
            b'RHDeH4d+db45d/Ltmx9vDzdqeRyPKUuRzJSNMQxakBRSymEc5bPPPvnss1Xd0N3tdT+M0zSk'
            b'PKNtlpguARDAosDIRTOQiUW8QOMqVDj2/TzPSOpr27TV+fnZo0cXKVx8+903fX/abjfG8LPn'
            b'j/fV/vLy/TzlIuGwD+t1k1L68vMvzs92d/dXMyiiOmdXq9Ysq5/3npmsdQAqIqmoq5phGPb7'
            b'/fX1dZwDM+aQVfXx06fdevVAmxgzjmMphb1la45Df317c+hPdd1utzvDjk0pmqsavQfREJP5'
            b'KCtYr7cohOIr2xrTOVMdb29//OHF8VTWm4vnTz9//vz5H/3il199+UUM09s3N6wlhRQXiU9O'
            b'ULI1SK2PIesH2fsf3k/6B7PUx/d16QVf1qnl5YcotmVsekg0FQghAGIuBRFTzgtuDryE1eBH'
            b'FcUfDHPLfQnMuFxv4zguH9TlJ7MUyVKY2FktZU7RsWFGKZEQnHPW+gVzL6CxxKZtc9Fjf/ju'
            b'zY9v3r7q42SaqqQZiRgyYI4poy5aIc05V94gIrPdbLrNdlU3a2/fvXp7GxVUsGQUwaW6A4CW'
            b'LS/GOCwuN7Yh5ZSKoswpV+QAYBhPkqK1ZmkpPxzuRWQcR1W11jZNk5N477ebCyJXilRVFbyN'
            b'aZ7DaK01IaScBZHbtia2KYeYc1F98+5dmKY0h1JKzrKoo4hMFq2auuuaBTMcx3EcR1c1ddP0'
            b'05ylCAIwWe+ZOZd0PN09abe77drVFQLnXFCM5bpdNyWDJBPncjrGZ48fP3u6GnvDFNtmG2dF'
            b'rZ48/pSwOuzvNt3ZeLojJQayhoqhAAW0ECgvebD6MXhflx6l8mA2WM4UIzAoqSAyLWWtH3/l'
            b'mksW1Vx8VS9i+ZxljsE5F2OMOaQS5zhZaxncnCKiGmOIWQGyFkIqoAV0kYkJaNGsWmKcs4p1'
            b'NquMYXbqVNWiBdEiEmICh7UiKBZZ1D2whK8BITEfh6NaPAz7m9vrUqJ1iFicJ1QisIAoIpKg'
            b'JFgYdO+6aQr746lqzfZss909aro+lWsgLgVTKg+heUCiKIpsnGjKoiEVo7QkoAhoSqkIHE/D'
            b'3f4ONKUcC+gwTwCQUgkhpqzO+qZdgRpnG2uroZ+bpupWja63w3h////z9WZNjiRJmpgedrg7'
            b'gLgyIrMys86uqerume3p2R6SI8tdWVIo5AufKLIUoSwf+Ff5tC8Ucme6mztdXX3VnUfcAcAP'
            b'M1NVPpgDicoqDiQyEoEAPAA3dVW1Tz/99O6hbaNbdCtA9S4ye1GYxpxzdp5uru+QrAlx0XbR'
            b'RwDIlhStjc2zd54+fnxemV/9OLx+/Xq73RqI93xycrTpexEdpp6JUt4CgGTVYmxOlXKyJh4/'
            b'f/r41bfXebI2LprQsHKISyFD8CGQ93EYhtevr/70x788OjvJw7ZrfcUbq5sMIXjmVCTlkVzY'
            b'jSmszIA6WQ4Pu8EOb/uMaq/wrqI1f3LOVeb7zP9pGlUdxtEIi0jdEIopgkEpyARqYoo2K8tX'
            b'saRpmuqhAIARnHPjON7f369WKx8C4ByyyTt2TsCcC4ZUTFUlFxVVZI5d7NdDtnx9d9P3m8Wy'
            b'LaQCtli0COCJ2y4459YP4+uX9/3GlC1NOvTl9au7zWa9XHUGfHO77bc5dgstaipmBmrqsaqB'
            b'E3rvkYio4reI4NgTA9IwTHd3d5vtHbFFX0sCNBWRzXbosxlC6wlDiOQ5lozrh3XO6cnTY0Y1'
            b'xWlKxZQ/+OkHnh2yM7NxSsMwpFIMIMQ2huiclyJpyqUUUFSQn/30k1/96l///Oc/u7i4OD9/'
            b'FGK4urz8+suvpWSRQoDOuSaGxWIR2KVpJLP72/WwzTGsPC3SiFZ8G05UwnYtkhnN59HGId/d'
            b'rl+8eD2NuWka5+jh4e725sp7Wi07zZPmXKahTIPmhCoqOU9pGid2bsdAnqOczXLt8yRBBDJC'
            b'QzCkmbZVzco5x2xmpUiNhrWnw3svAFNO7Nw4TYDQLjokylJlDQwQpmmKTRST6he5TvQlqvt5'
            b'Q/AximkphYjGadpst2bmYiDHVSw2NDHECGCOiOtoDEJRTZKKFiVzDY9pfHH5YtuvydNUJil5'
            b'dbRchLbrmiePHz9955mjeHfTD1sJrjPE2DQGcn178/Ll5eXVw/o+9YMBeFMEQxVTVec8EZci'
            b'U+2RDBGn4FYrAAAgAElEQVSJc0kpZzMgx7FpU07r9bYfelEppYiC98H7dhjSw7rv+1KEVFmE'
            b'TVAybTb9MPRqhR21iy7Epqi6ioWULKKlqBB7Tw7R6lZbi45jKuMkkjWXXKbLV683d/f83rsn'
            b'x6fsedz2/f36u2+/GfqzGOPR6uTR2UnXdUerk74fv/4ahjVpwouTd3/1y//26ZP3v/rmxZ/+'
            b'8M3mIa3vVbInDmnCq9c3aRiXi8XZ2ZmI3d1dMzM5evXymzQ+lJ9++vTiomscQ5ssTf2oYp6D'
            b'Zw+KVkR3GToRqCruZi7s94Y7vUitn2ufhFVQ9HATBwAitfGYp2kSEQWOMY7jWKQQwWjmmXPO'
            b'q0oI2bViV5TVzGKM9bAV+SulFBHv/VSyn6a6aSDHFdwXUVYgQA7MXBVzNJWcNZlTRDg+Pg6d'
            b'm7DIqxe3m4c8jc4hI1oV48pQsklBISq9rFYUop8S3N31IkjQEbdSsGJpYGqGpgxAAFSyeu+Z'
            b'vZkUmSFTh2SGUtCUgu/YWSnJVCWiCg6DDL2UbDkNMSBTVNUyjiVruyAwF2O7Ol5M03hze89n'
            b'z8/VtIiZatO2R8fHTdOImWQpWUoupYgVK1Iki2q5vb7sN5ury9fXV1e319d/+dOffv/57x7u'
            b'btEAAVfLxcnR0apbdYtlzun61dV3X78cB120J+dnz8pEf/rjd3/8w7eXr+5fv7xzFI+PHi26'
            b'lQls+m1OmR0R6d39NaKdnR0z2u3N9d3tVb99WC7a4Cg60pxACyGWKfdDr2YIBlRtZ9+kqjNG'
            b'pXPeAwCIBFUUlKkySKVOG8S5ha6UEmNERCSuYdEAjCDEuNlukSgEn3Jids77EHwuRUWr8wNC'
            b'BDUwJq7xdBj69XajpiradZ3OREoNMYQQzEwNHRMbVLQMCFJO/bAZp7FYSWWKbTh7fPro4hEF'
            b't+m3w7BVUccejXKabm/Xr17dre/GlJwplwKxiRxIRKZJckaVaOLNjJG9C4RsgN5777yZFhHn'
            b'GYjEJJdiiMRITES+KoyrmSGJKhiwcwC87aec1MybOcSgytMowyaZWtvF5aptF9F732/711eX'
            b'rpgSEoCS86vV6vj0JKUkUjDEzeahH3uTrEUkT8zcto3k9IfPP//tb37Xdv78/DznPEzj0eJ0'
            b'ykJN9G5h4h/uh/W23N0+vHh5f3b24dCXu1v9T//pt9Not3frrjt69vT9k+OcUrq73bDDEMLJ'
            b'8dn15avXr1+fnhw9fnw+DMOLb7723q+Ol1bkL199iaDvP3vn0fFSiY2dI+SmIfa5jEZW2QGI'
            b's+pwJSfPbkoVjSvxAQlDCBVvyjmrCCL6QCEEU6zbGVX1TORdv35AxlRKLTmcHB0558Z+wAaX'
            b'y2Wdv7rfe9Yit1MY05SmqXqvUkrt6yLGSHG73RrC8fGxj2HoJ7DcNA2aGkIWzaLDOA25ZFN0'
            b'1IR2dbZqj5r1cH/18JpQgoNSUgiOmbZDf3uz3qyzaRObLk3imEVEExO2PmSRkjNrbdj1SI7N'
            b'DE2tjvdgD0BSTKGI5FIUUA1YQNUrEZNi32dEIwZgp+LKZJqBMLB3CJ7QoYGIxBiL5GEst7db'
            b'sTxMGVCZOv747362OjqOTTSznEuapqkfpnGU1KMJaM7TGmxqG2KWNG59CAgcgvcuTqmUDIiN'
            b'imdesOuQli4chXhsEqX4trtQPDE8SuKLxHZxdn7xrO2OpzGJWs4l5zGlpCLee2JnKpvNBtUY'
            b'GZFVDcwUTFQuL19PefIxrI5WoQlTzmNK6PlhfU1kCKigxOQ8m+mUhjqBhpAdOgJ25D1F5z2h'
            b'OUZTSdNYM6roAxPd391Vvl0MnhCmaQBVAJMiOScw8+yCj6hgJkerVb/Zdm3XNE0pknJCIgOc'
            b'Umq7BRM/rB/GafKeVUVVzBSIQgxm4GPwseXofdNut70W8T4o4FSSMt6s70ITv/r2q6PTo+5k'
            b'Sc5Wx+3d/fXvf//PKQ9NEyhwu1w0TZtL2WyH7bCVPCkU4oohhaZdgLnNZuiH0UwokI+eHNd9'
            b'Hzvn2HnvpmlCpEW70CIpjWAqpTQxgllJk6kSEhiAEihKtiZ2kiH48OTxk4uLCwDZPNz341bN'
            b'iuYsSc0MqB/K3e12vU78zqfP2ZFo2fbbcehLKWZiJa8Wi2nqp2m7XLTvvvf02dMnbRcQGS2Y'
            b'chEsYiVBymjKCjEXzsWJckk4TThNOk2WkjfrDDvvGucbJFeKlVRSLm0TRWQah3EcdTcBgAkJ'
            b'KaeUc9mV4URFYhsXXXtze311dQloTdsaYcpZTXO/NStIEIJnppKTqQQXShYwAEOr8cwIgESV'
            b'2Cprpu4EvfdMrKqVQFI5JCJlGsdxHFPOjhzOpC5jQGYmwlIKGIQQELGqF9W6YRX/F9WcUiml'
            b'goJVEyBLJkcI6JuGnBMzZmeqjLBYdEC47rfjNAJaNtuMG/SOPU1lSiVvt+svv/xSpfzNL35x'
            b'8fQdAb27vXlYr4N3p6enXdsgSCojEfoQoo+qpvPQJyii5BwT7woThMwGIFm8dzFGkYJmwXtT'
            b'I4LgAqKZoqrUCVFMgZCCb1WFOYTgGajyi9SsqNbGTANKuUxjyklVwW22t4BLQgdgRbKBIjgk'
            b'nHIqokBMLgB5A2bXxAbASE2LpiymYIakGIiaGDoXImMn6qcRiExhzhMb7zF6VS0p55xNipkN'
            b'276UUnuO51rIPvnNc+daFWXAXUWFyW82/e8/+zwN40cfvnt8fHyv+ejoaH2Xpn7y5GNwQK5+'
            b'TklSDFSKISGRoRQAUOXCgJWGgM4574MhVul5RAQiqVMnrULgRkRZpYbUlFLTNOxwvV63sakU'
            b'nVJyRe2D913X5ZwPcnkAAGIA1DRlH4NjN//W5oMzqpa869U258K333y53g4P/fby9noqg0Lx'
            b'LRu195vNts/nZ1HXt5OMHHB5fNTExfq+3wwPPgBSRkiqWU2IgBmHsZixJKxDg6CWVEkZPCI7'
            b'9sGFxKzOxeirwDQigu7GtoMBIhgZaMnK7AndNGUpKGpAjplzP7StjzECQJFUkdK2bV3Og0j0'
            b'DbddrAPWqM4LAXry7Hlg6vvtet3fP/QikhOkgaU0QE0bPLnAzD50IcS2WbAPwTfMzgxLKTUC'
            b'iCiQEu7ZKQVUzWRIAqgAwMyqZa/MriXXYS/b7RYA2rZlpHEc0jidHi+b4Dbr2y+++MK0PHvy'
            b'uGsXUU6m9XozbEfbNicni2ZR51a2sclSRijFVCErmqEhooDxbk7fPBtHtbZVVgcWwjwejFzl'
            b'vmFNxmOMFfoiwpwzGiwWC+diNfppmlJK3nsVc75WF94M7anNj5WZh6agwsRkUCSjo4eHB0SM'
            b'beOcG2X6+puXD9sH33p3x8hwefc6NEGwM1y9vu438s04rYEwRs8B2Wm3cBePj66u7kwzsSAm'
            b'yZNpJgQwY2QQEAAFQQMA8pWdjLxzz1JKCXEuJNR1qGeICFSLqJnpYFMIDhjGISEKgJaiOe9C'
            b'DbP3HjAAgPd1M+QZSauYdtO1RITAoHBxcfH++++fnZ6s1+vb29vtdn11dfXi5W1WRl60bbtc'
            b'Lttm4b13LnrvwciIEVhEi5RcZj1+RBXNJc9WpaqganV8nqScc84TqCKi99y2bZ8zM9Ylr/RO'
            b'RVDVGONms4lMy+Uy9f1nn312f3P9yU8+6Jw/OjopRfM09Jth2ZF3nokx0FiohjyZh/F6IjIj'
            b'FZg7xIxMMRWdsqSUAMC5EovWGrMBVT1mKwLE0XnnqUgq2SSXsZScUwzeMXvnwGyaBgANHKLv'
            b'yDkzD2pqpSa5Vee2GpmZIahaSWlkpTIlIkLHsWm6o6PYLq++/KaguTZ89PGHq+N4ef0aOIT4'
            b'ZMqxY+caiUaD9H2/SW5sfHN8tshlmkZpOxeD3/Y9mrTBS9tICYCsxcQUduwPJoo+BO8Baj9P'
            b'D1iKCCGWUkzADGsWoQq5aJFsY+kWjXeoVsDEeRIFNfQ+zFcOUc3Up2nabtd8+sGxquYkOQuh'
            b'a9vFcnm8WBwdHZ09On/y+OL58/c+/PSnf/PRT37qQzeO2LZPj0+enp49OT17slw9cqEjjogR'
            b'yUuhaZRxzNMoIgC1nxxBtJSc6zguVVWpDdpZpAo+I+1KwgjGRDknVasZzDAMUnIMTQxeSsol'
            b'V2qCqU0prR/ug3ch+q5p1WwaxpxKYN/EUAvQBiAgokVQobbgi9FuCmu92lLJVR2plhT3XYc4'
            b'X7RYg7L3HglyznXTB2BVen8ftQEs5+zZh+CcYwOhHcBWbT0Er2Y7XUEk5DyNUIp3ROxSKSHE'
            b'J0+fqdG3L15/9/Lq9n57/uTdn/2rvzu/eNfHI3SLJMDehnHYbkcpFmI8Pjo+Pjk5PlotV0dm'
            b'slwuu657WK+HvidmNER0CAigVlEYxOA5xNB1sXaZ3d3eDcMWDIpkAArcqNYBfTY32ZUiRXPO'
            b'1QGLKAAgzB2/ZlDPpPc+RF9rD+M48tHzY1UoGUpWVQDzgB4wTJONk2kh5Ma5ZUq4XqeUuVs+'
            b'6VaP2nYVYmfmUraUVQqIQEplnHIuAgqIhEAAJpJMBVRMtTpZUAWzaRxUxBHGEByhVrn1kj27'
            b'UjIiOMdErKoGSkgipYmBkNI0MOLRagUIVzfXqlIAXGzYOcmaUyLAGCKAErF3hIxmqiYASoBW'
            b'gLEKeAIAEjEYaFEfY9U0nxWLdXfeVNsuIkEpuTYrqwrz3F4BZiklAHWOETGlFJyrTBtVMTVE'
            b'C8yhCTmnECNaRdMAABw5ydmxmZbYNrHp2m7ZLlYnj57crfur200BT3758Sd//clPf3n66Ony'
            b'6Ilv2ofN+v5hc3fXq+LR8dmzZ8/fffe9J0+eIsD9/QMgex/v7+43my0wi5ojADMEQQBT0TqJ'
            b'2dNytRqnYRj67Xajpt57NWR2bVyoWK4Ki2Z18lXlSgKA1Li4s1PbzyqCqhJlpUjORYry4588'
            b'd64lDCI4DjIMebMtm/UEEMe+DKM+3E1ffPndZ5/95fLyHqjJhXOBnCVnSUlSLmYASNM4lSLV'
            b'JdaJDyKSc8plMlN8o7UnCMAOmUi1zKTgUmSGlHyexhBCjYN1sCwRbvtetKiKc+x8nc8xmqpv'
            b'w836fkgjEseuDS7klEW0qiJ7z94HIhTNKkJghAgKTHP4J6JKBK3nr8g8GbAy3EVEVQBktVoB'
            b'QN/3TBxCqOzQuVVaJOcMYH4XVrxzTRuIsZQEpkQUnG+bZtj2TRMRAIHUAMy8d2baRbfZrrtm'
            b'cfHknabttmM+e/R4yPaXL7+L3dHlzUNWvzh65OPy/PHzi3eevf/RR01c9tu8WadS1LmmiV0I'
            b'Td+PX3397Thl5+LDuh/HHGPj2GUpYLUYpQZFTYnBOV6uFuv1ehj6aZocu7ZtAdA73zatFKks'
            b'kv2QUUR0zs1Z8jwCa+6bb2Lce+sK+FVNTY5nZ6ZMGAhbcl2Iq6PlxfHq/Pz82XJ5FuMKMZo6'
            b'hKjC4yhmrpI1RWvOJCoiUhwRgIEpgFWpcAIjBEKhnScGmzNDU7EiTMhIYEpW2cMGaqAVrNZa'
            b'TlZVAIwxABiCaV1sVUADBAULq8VQ8vXd/Wa7jbE9PXuEBldXV8uuq6R253jRNsumBdPUD44b'
            b'MzOVueSjYqZIqCqSs9j8eHVLTdN4x2mcxmHMKasKM4NZ3/cnJyfTNDlHRLh9WDvmrm377ZYd'
            b'eu8ZKU2j5tI2cdG2hgYIBhhCDNEDoqiJaPDOJMUmLhYrHxsk50LzsJ4U3O395vp2CxDId013'
            b'vO1zFs7FEOPjx+9/+tO/ff7sI4BweXn/4sX1i5eX19f3CA7ADUMWBQVOWRXUMYglsWIoBlih'
            b'PvYOcW6RNbPqabzzzvna3zaXyHimYjvnFGxKk6h674loytkA2qaJoc7/2Ut1VkoRuyactm27'
            b'WKzaduFCG3zXxEUIDXFUNSlWsqiiKhC2bYCHfquwbwI1NKttxdM0wjxWSFQVbSc6oKomJnX7'
            b'LTVvJSJgqDOUiKhe2XZQ4wPYzx6sfARm8kZEKiZSx06oqhKMKVMIPsSplJc3N8MwnDTt+TtP'
            b'Hzbrk+WiDS2S5TwpyEm7XMTu+r43JE8MTLVWLbko2EyO0DdKfyGE6DyhTWWqdJoYQ30/XdcN'
            b'w5BScm7OzOpW1AeuqaGZOOeQtSbsZFi1MMjURMEQEQgB0WIMnjhG75xDcgYVDSF2jRQwcFIg'
            b'TaYIvJkWuHx1edW0/ngVT08+Pvu755vN1e3Ni+3m+re/+Uezyqx2KtGIwBUwdUGRTUTrHD8R'
            b'q8WlPEe7Wfxid8JtGHtERCTneRf35kjnHIuggIIiMRKRgJJjKMA8a0Xtl889fvJR1fGpM6sQ'
            b'vSmWzONDXzUUU8qykxpHxqzZUPfN7AyzAofK5JBqX1KWbKqASMwqRVVNy26AIFB9vhoCzDIx'
            b'UClSPxxW+ebmnDNAlGrSqAYGVkxT0RCiI05Jhu12mjKfcHNy7FpLhjYMgTk2ftE1IqVPKSes'
            b'wGUVDFdTMjAwIh88i0CWAgbR++gZyXDmpubasJBSYqIY4zBsSylt8E3TOE9qRTTHGOsUeFV0'
            b'rsIOZCZzRmUgIkZC6DxzYBfYddE755qmc86ZoewK57PKA8VSdJqyIJciHNvF4qLv+6/uH4LH'
            b'05NmuXj67PkjKf3PfvZfv3r97Vdfffni5bfrfp0SEEUfcMr3WkAKAgBz6JrYdV3bLEop7ELN'
            b'FFOaauzLZSKoczf93AmMisDEYKLOETCZCTF7x46DY04pSS4190LkHQMO3fmjp3W5c8Ihp2na'
            b'TKOkVCfeIs5bg91+DlRxqkaJiHWbRbu1F0Q00No6ZMWsJu+y32TNoI4p7MamkdXWUd1fN3vy'
            b'5/dSw1njChUNSMHcnHsDMKJkTQBmyC4UwJtNP47pnfNHuZZ9QVg5IBOZJ350djalNAxjPw2l'
            b'FAQjdszESBRYxdmkVptdzXLOjnifis0noZRSSoy+IkB7vo1q5QtgKQXUnK8tGFqbKHPOqorI'
            b'gcgFx+yC855dCKHKiiKRCIGiFsk5m2gphXyswGzd0a2SpFyKgmkYhjSN2xg2MSA7ayN1i+d/'
            b'+8sP/vZX0Pf9dy9ffPnll1eX3xUtAE5R5lVWNyVUy2iiWlSyqgCqD3WoKIOaahHJdVOMiGY5'
            b'i6kVdBwQDam6c2YGxc39pqQsokTE7PesODclKKWklEspWkyKSc5SZrIvzZlIzWqLWlHQvfgG'
            b'zh1Us6Ce1n0fKCLXjgQRYfI7szCQoqZa/V/lo5vty8X1qAZ18uMb1m/N/M0MbGb0mZmRQ0UA'
            b'RtNSCqh6Yh8DqA1ZhmFIUs5PVo+Ojx3ZUKa87dsmtMsVQu2/QgRJSGIFgYBAVciQiBxXKVk1'
            b'kVKKMYfgY/AVlQ7el5LGcexiIIOUxyLRszNREwWeNS8VIWrYfahKJjA1897NTDBPREAMMTS7'
            b'dvv5I1dgabvdmgmgMplpGqfMPpbU39yPoW3bEBH8NA2b7bjtwbM9MCAqR44xNs3R0+enF0/+'
            b'Kpfxz7//7ebh+ur15d39jYmuVouuO1quFmB5mvo0PeQ8OgODLBlKEUIsZkoQgo9NAwDboR/7'
            b'oTauOefmdjbvAcDKG/IR7po0ERgB3dXlbY24qopGROTQEaGKiJa6casVDkZU1MrpntOgg++I'
            b'JKYgaoTM1YkKiBoJGM0Z05yYmWpxu7rKzkQRwObh8W/GTHx/hAkY1mjPTEZE7EBzSs4cUh2u'
            b'YVWmxzXd1cO9EYLjVRcb79g5cqyGBObZcUfRu9qelXMuKlmziRJBdN7MoDI+GHLOdeF117S4'
            b'J2Dhrg0/OI+7uXYVszGDUpLUJ6OJMJFzRCHGJgbvPLPzzgV2NScjdEWriFcexv7h7vbm5ooJ'
            b'AdR7NpNxHI6CG6eh7YKCTmlQVTQgbpmZGLWIggzr9LCevJfYRe8DAf0P/+N/2N7fvHjx3cvv'
            b'vrm5uZrG7VT64eohejSbHLnj4+MYIaXh9ub1enN/sjpznsm54+Pj5dFKVa9urotMRkhs5MB7'
            b'Ju/qgrDHEIIWMyt7w6rhh5dPf5ZKUVERlSJS/9MSvKsdJQSKIITKpMygUsD0e1+Vq1LVeWYd'
            b'DtwN+cbaugCiWkRVVBVBEasuvu5ZVAhQKzwGCrV5E8B2TPBaBgYwmh+ogyaAkamYE0RDAiqi'
            b'RQoguuAAKUnZ9pspTT76btEhs+ZMgI7AO/bR++CcY+fYefbekSPn2AfnPAMCUcXDsObnRHtg'
            b'VQGAEJ1ztTOH5um63DQN8UwkRITa2VyJhzEG70MT26ZtQmic923bdV1bNwQGVNRS1jHly5u7'
            b'r7757k9ffkHOG+BqtWq79u7h4fjkOJUEDgoUQGDnvPMAnFLZblOMCwOfhMYE46RJaEowTfLF'
            b'H7+dBl0uHz17/sFHH3363rvvn548WnTdq1cv0jSKjKGhrovBQy5jSqNjRqTQhOVqsVotQ/B1'
            b'vnz9ToxNE33wROijb7vOIYPNopvO+bplB0CHUpiAiQ1BAFSSKCJon8dKm0CoNVkTk33CcxgK'
            b'a5Y3ZmFG5wIAqGatU4aqLodqTUEAgAiQyCGlMsJe03FuLq22RdXmAGYkkQHn5gdDg4r3KSKY'
            b'MRjU0lBVWkVEAMo5JynHq4XkPOXh+n6dc05FL07PlrElqVQHQlBm55DUsZkV05RSnYNaRAZT'
            b'AIjBd7WHWNF5MqNhGtG0a0JJ2UdPBGhqVjeSGIJDgqpUA2qimS3YjuPAjD6wZ+c8ee+qpH5R'
            b'KGYqmIuORYcE99vt9cPdZrtdnbYmysygVsaJAaahb1YLVJSSypQmZTAi4hjC9fV1bDoOPvqg'
            b'YKCax9SX1Pq43qS7h5dmsmjD6cni0aP3Lp6887e//PsXL/7yzVefb7fX0yiACHgUgvbDCDAV'
            b'S74xF4v3nknbtk2TjJrQyDkXg1PUEMLRYjVA9Oj7vgegOuwYU0IEfnTxAZRkUkAzmpIVMkUo'
            b'WpKZgCnXWZKAWFkBaqCqUlSKqYBqhdjRKnepqBSuib2qllKrAGhGCFw5Pqoq5VCvsW4HDUCt'
            b'ItNYBzIwMdcRSwCmswgMEgMhACmgIYylGJN5D8xGUKV90CxNSVWCj01si8Ddw2Y7JDA8Pzqu'
            b'aUIg5x1HpuhddBSZF9EfLRaLGD2RJ2xcaELwYCgJTD1b9Nx41wbXePaemMw7ahdN08bYhBi9'
            b'c0Si07AVKSH4JkTH3DTN0dERELZd17SRmENwy2UXPE+pZIgGLcV2PZXr+yEBvLi+/b/+6dcF'
            b'ODTd6dk5s5uGKbpQxkTI4ySBgyYtUyJikSwlLRZRJeUylNwTCFqRMplkRikyiiZRMbCcZdMP'
            b'Dw/D7f12s82nJ08+/OhfPX36iW/OxxRvb+zurhyfXJgVjkltfXv/ahrvGYOV4HHluQvcgMk4'
            b'9eysXbQOMXK8eX2Z0hg8xRhiZAUBVL548iGBoQmagRZTMS2mArUdZbdf291ApOy3b/vspyYW'
            b'UC2i9mDtrIUQ5g6D+c6bORGHO0GcU1c42GXu/0L9KwdT4wytDjOqTROOai8ogtXoi0gzmFpE'
            b'DSpKXHf769s7BOuWi6ZtDaCUZKaeuWsbx+yIgnMx+MbHtomLpgkOPbNz1ATfBB+8a0KITUQw'
            b'dhS8C947JkBABAYwE1Dzzi26rhIiEBmJvQ9t0zVN62OIIYQmMnEBLBqM4qvru4ftEBfLb15d'
            b'/j+//u3Nw9rQxW7BPpZiaNQ1XRM7Aq6dWwgABs5RXSnHJJZVC5hg7UDTYiZEMI2jWlFRVRXV'
            b'UjSlMiXNyS6v7q+v18Tdu+9//Oz5x0Ttej28+PbF+cXp0WlnkIiyqfXbMo1KGKtgvqGJiYGq'
            b'5H47rK/vckqEMOUxlck3DlG3/ZofPflobzXzdnpmJeD3DAq+J2i2yznmfG1f0N3Zx5tX0U4F'
            b'dG9Me6vZP2f/yPdMCeAt3Sv4/q3+lhAQiWszYdWNQkDEuo+r4wV4J8ctpfTDZsi5iCoZe+9C'
            b'ZEcICEhgxuyapu3aRdcumtB47xZdF3amUIXOY4yhiapaYWnnPTMzEjE75iZ2zK6OtHQ+MDvv'
            b'o4+xadu265q24xA8B2BnClMBEddPZdMP4Lifpv/yu9/94U9/VoDYdG3XEbk0ZSReLpfBh6mU'
            b'YkDOzeefqO7WAQwI96jQfKnX4T8iiEBAswadquaiRUrJ3jtAeNg8XL6+HKfx0fnjv/7rnz9/'
            b'9+nl5ethKKvVqWRkCsvVMpdUNAOoiOWigI6Yc85D30vW9cP9Ytl9+vOfPnp8+rC5Xw9r9sin'
            b'Fx++ZUCw1+PfmcjeLOpy0u72vWU/GHNaP95bdoa721uvOjSpf8GwdhDwoSuboSzE2ZhmPAIM'
            b'Eb13FbRg5h1oYmKCxEMeH7bbzTiIGXvnQ2DvayGCiBGIgRjJO+d9aLvOBxdCiD74GCqv1RGz'
            b'd46d8zPI6L1vY9N1y7ZpmQigtv47H5rFYrlYrUJsY9M6H4BYgUUhFZmyjQVv7texa8Xwn37z'
            b'28/+8CcBQnbtYkXOq6IBRh9DbE1tTAnY7afqVTup58EQDldwvpAqWZKAgdRsbgkAAAA1ZXaI'
            b'mFIaxiHloqKien726Gc//4UU/tMfvm6a1bvvfxCjA9JtvzawYchTFu+jD1EkF8n95uH45OhX'
            b'/82//vf/3b/zDX/2h8/W/f3ipOOT8/cqocJM6/mvnqje33/tH5k/0oEhVrPYm87hx5vBre8b'
            b'1lsGtzeUt6zqh4b1A9O0urskgJmtMKOmBgAV8a9VeRGV+RLGSYsQGXGfxvv1dtsPCujYtd3C'
            b'Oe/IqWopgoCeffAeHRG7EKL3wfsYQnTeO+fbbhFCdC4454MPzoemadu2LXnuaGRmH0LXLRer'
            b'k8XyCMmTD4BeFYthUUhiWalPkMSGKf3xiy/+8Z9+c7tet4sj5yP5OGVRgxjbpmkAsRQ1IAre'
            b'0Gp1TkoGsCq1BXowAxYA5skdmRFNRIuKlCruVs95yUVUVI2IYmyBaRymm9u7IsoUPvn4l2dn'
            b'713frEPTHZ00r15/m3UChCmJFIxxYWZTGgCKj/Qf//f/8B//j//tJ598eHN/VTB/9Mn7T56e'
            b'8SIipG4AACAASURBVMn5+4dredBP/MY3/NDNvOXh9r7n0KkcJmGHB/++1/kRe/pRw/rRUIgG'
            b'fPicGnwRELGUjIjMrgJkZkaExJwNBLAWyYpYymm76a9vrlPKRdSH0DRd03SuTls1FTNg9uzJ'
            b'e+9DaJoQIvsQQpzluWscBqz3t9se0QUf227RdaumW8S2IxfUyJAUWAGzYlEohsV4Oybk8Nnn'
            b'n//f//hPQ84hNArcLlfjWFIRJt91Cx8bUTBFDp6dK1oBMqoNsZV3MJ/eHasMK65WxBHNGGCt'
            b'hR0sjfeBiUV1O4wlqw/NYrV6uH9IxfoeH52/+zd//Qs1+errPwMbEYQYRRCQmHmaRtHx5Gzx'
            b'b//9r/6X//V//pv3ftZ1LbTlJ3/1wT/8279//OyCzy7eR9hf699fuV2gmX9VY+IunaqjP/e2'
            b'sw+dCMBEvLOhH36vFvlWJAWAtyz1XzCsN6HQgBBw51gPsi40QOb6NggJiJmJAZFCmLKknEGB'
            b'XUDCvh/u7u7vH9bbYch16jAhMCtCVqtH4VqpJCLneKfABkTMzvtAvO9ndmYU2261WrWLo9gu'
            b'OEQkp0YCpECKpMZJYExlmGRK8ury5ttXl7/7/PPrm9t2uQptl1WNaJgyO9+0rQ8BkascdNVd'
            b'kpw9s2euFha8LyUzuxmNVd0P3DNVT0RIWGMz0q4BExBZRLMqElXxvSyy3faro9VmO5aMFTJ/'
            b'/4MPH12cffvtd0dHq26xEDOVpJZy6c8vTv7+v/r5P/y7Xzx//0ybETBjUPJ6dLYoNvLZ4w9+'
            b'dF0PgxQceKn6YKVLVybkPtLt7+wzMDuoeL+V18+Sr9+3JDtgN/wLhvXmEYM5gTowOCZGnBua'
            b'YTdUtQZNURAFJnbkTSynlLM459uuy2JDmm5u715dX95v1kLEIVLwzOxcMGTRqtnGVVfDNy27'
            b'EEITm65pOvbR+ehDDLFdLI/axTLESD4geQUqBoDOgAydGKWsw5i247Qd0xdfv/jHX//67v5+'
            b'dXKqSHV8xN16Q+y6btF1y3rZMjOxqzsGEQkheO+zlFogyjl7H/bUZ91ftzta5e6sookWERFJ'
            b'ed7WiNo4TuM4IXLTREOJTSTyfT+OQypii8Xq45/81abvY4xT6ofpQaRHyp98+tF//z/9m4un'
            b'zbP3TgIRgV1vXn/78ptcpqub13zxzkdQ1e52Oojz8jCZWWWp7xL2nf9knjuJd2yvt3JG3Y2i'
            b'rGDVYVjUGQudn7a3rf1BiPbINe6r3Yizjz80eiIkJNAa6QCgtmfNlaJdTDh4X7UZWqCq1jCR'
            b'Iw+AIjJMU6kFJOZR5HazfnH1+tvXr16+ftk2CxVl50PTOOcNsJhVOpgaABIwk3MhNk3bhbZz'
            b'oUHiYphFi4IAATlgp8bFYJjKdkpZbJjSN998+8+///yff/d7JW67BTEbYlYdc0aik9Mz73zF'
            b'osVAVCvZSTQ7z5VVTAg007wCApjOmXm9j0COa0fF3DwCdVNPGGP0zqmKSGFE9p6ZTVVKJmfE'
            b'oFYAgYinIY8DOF6eXzx58d23v//8N6+vXj97dzmVdfDYHZHgDfoxLnjU7cuXL37z29/85je/'
            b'lZL56Oz5D5PrQyup72mfe5Uih+7hh69668G93Ry6mr1Xo90GBw/wi7cMaPfaHwATONd2duVG'
            b'QjAE3JFmZ1zN5prjTENjYo8zuGRoVSodiQzRiApAhpJFs1kGLWJ/+Pzzl68v1+ttnzMic9Ms'
            b'VkfLo+N+nGo/LLEzYgUsakWUXED26AI5D+QRSQCLwKYfyAfn/WY7/PnLr/7f3/3uT3/+y+XV'
            b'DYXQtF0IIatt+zGX3LTL07MzLbDHpOtHIGQkMxNEQKQ3p/QN8ge2q2ZiTe/1TQ5Ts65SSq70'
            b'jJJzTjP9WCWX+miSMhkKQHZM3kURLhOXwqvFqls2opsPPjxeHTkf9KsvL19d/Unp7uy8Ozpa'
            b'3d3ffvHFl69evAbF0+MzV/s26SDpe2v54ftRsrqow5ccuh/8Pvql+gYj+J5NHPx4+KpDEzz8'
            b'8cBQcB9SZwZgHYyzO9xbf8uMZtYEcC0yBmA0K4BqxsBKCkCGpGaKKqpScdyik07jmDr21w/b'
            b'm/s/wh//vOy6k7Ozi4uL4+Pj999/3zkXnEP2cxVB1VS3UyYicoGoKjdClpLFtuP49YtX3716'
            b'+fry+v7+fsolOL9YLcUgpbTdDsWU2DdN470XETM01aqMDJU4TYTq6txqeYPsIJuhOWQPOwIn'
            b'kgOAUoqIIvKuCLu7mDWr1FK5zC7PFGRuEp2GUayPnqBJHgMYlhLHnr74y92ji8Xf/e2/+auf'
            b'LpGv/vmz/3x/+3/e3eti0Z6enjrnbm8upyE9f+e9s9On77zzzO2x0IPFeGM3h2QsOAhhex8D'
            b'B44NDlDQ/dMOk/RDk9rr9B9a56Fj+xe83f7qnE1tJ2ULgGaGQAZSqTvV9gB2XhbAVMAQVSvB'
            b'cH46MjKqFkUA8+AUVARkKubIHBIxEdF6yttXly8ur5n51//ld7VWc3x8fHRUS0GRHDsOAKJQ'
            b'RKSfxqGf+r5PpVxf3b68fH1ze++caxfLZWzMrKhOOaepJNEQQtM0TdOY6dgP3kcyAlUjAhAz'
            b'hGoOaKAEO9ak2d5JzWfdzGoej7vpeUSukg0R0QdGCqolqwCiqlSkBitCiaQGMpaH7ZCaBNY0'
            b'wXnmEJq7+/ssm09+/qhtj84fn/36N/85xiA5PX/+3snxeUqyvh+OFueffvQ3Tx5/EHzrCGux'
            b'RcGkomxY33BdKps1u2wnN0UVJ1IDtNkZ6Kw6DHVekgHW51iVSPoRF3Xok+DtkPfGqg79WY14'
            b'33d4tRDNALtBTTsbmiVAkHcDUXavBQDRSuixOk0TYK7E1A9YUTxiJqeqBmU7Fu9cCM6zJyIB'
            b'KGYglrYD9uOr23vEb944UYCu6wDRbJZJmnLJOatCCEFMu66LbWNmfb/JKo5DFvFNWMaWmdWw'
            b'lELsQggzLdukAsPGUmnzgDQXPxh1p/lmZmSgavNSKc4dZkRmaCj7pwFibS+v+Hzt26l+g4jI'
            b'kUeepjwMadoWtFY6bhrnPJ6fn93e91/++Xocbj74qAVb/eTjvwZeD1u9ux4QyvZenp0/evfx'
            b'T47D400a3N4x6E7hqZ6m6lEOHUmN3aZ06LT+//zKj1rS4f0aPn74TN01Xv0g33rzzB/+rf3T'
            b'EJ1qIeBKv9kFzPl9IgCwmRoRmiFVlgMQIoqkOvEBwdiAsDI+XHPEpZR+yqUfwNB59i44z6mf'
            b'kICQidGxZ0eOPTF+9+oKmWZonpgcN91i/uuqInp3dzdNk5nFrvWda7hV2J9GhDp9Ok3MHojQ'
            b'CEB0V68horrt2+VYqKpEb84/7nS/bDdF1gycC2acy1SKGBQ0MVCqOSagioGJidXRlmBshWWC'
            b'grp92KQkjjeb7e1fffzp8fHp1dWaGBA2P//0H7K8j269PKFHJ89LhrMjPl2904bTCEfiG7cP'
            b'c9VtVpn8g3XCwzeNM7/K3iByu9sP06kfGtPhrQ7s+2Gd8ftW8uPA7PyWDn6JVveSBgBQd6wH'
            b'Od9ssggIqgZIWA2OFBUJjAyAgQEVARCUVNGMAY1wO4zkOHaLhScEFs0lyTilrluaiRmaSVEr'
            b'KSdUAF0eHRvMEw2yqBYxm+b3TfOl0iya2i42juPZ2bIfp2nqETnGlphFNJfcNIxar21QJFME'
            b'RREA4NruocqIZlpUCSBaRXbqQNDyJg/JUtg7xx6qQ7BKL0BEZEZGVoJiZpLBRJUa1xpTjzlL'
            b'Skmn8gBwP053ry7Do7PHJ0dPyabrV5cnp7I6abuO//6Xv3j66MmYS0fXp8uLFk4J2gZbXhw9'
            b'3lcu8UAPGKHywN+E7t064r5KXYU8Kx9BRODHbvQDz1Qto7ax7ws+bwz3INvbZ3LV6g5dmpmB'
            b'ISHVqAcGVu/RvAHUWW8Fd/guAlLNKmyHpRpWvo8CGAFUFBJqMmtQkxQOwYgrTyJLkUppRJrF'
            b'AM3U5t42ERG1KpZcexNk16hYzbpOrqlYeYwxhIaI+rEwuxg7Zley5lKYXdM0qrZnmGm9NmbG'
            b'IdaT75yrHgupTnxCJlelTUzflG6HcQjBhxCIEMCQjBGJMKUEYISMiCpaSm2ZgaPlkRlOKYlk'
            b'RAPNBqNzsHlYO+J3njwb+r6U6ebm6umzdz784MNHjy6WzQrAefJnp2cRwn2+fVhf8en5s1oo'
            b'BDDnPDMjcM0Ia75Uk1wFMxA1wdpgYVK57rvvIHU7VTOsKhINYGB7Lca3squ3DGtvQ7UcWfGN'
            b'/ZNV1QxUbYf577+ADN5UntEUQaFSO/ZpYDWpSqzBWser8nVzpxUA7joiEaFOywWiyiWamZMI'
            b'+y+kCvtVgZAK/nnnvPfBOQ4h+MDBx1qu9r6KWroQGkQCJCIGqH2FZoZmnl1E9KoISM4H56IR'
            b'Ox8QGAChCsBTHdJF9TKo10VtwTQwVcu5ECESixQzZaYKd5WSRbNqwdqWWbQO6qkofq1fz2V8'
            b'MxFxgbJMBsVApIwiGbLkIS3b7v7hxrFdnB+/ePHtoju5er15/vyTT3/y8cP6Hk2KjNvhCtot'
            b'8DrjHa9OLkSKasWr6ptnRJoHwSIgotZ8pXaY7xYadrDqQbR842neeKwDpOrw8RoL9onUIXjx'
            b'oxHwrZfPL6y8UoCdB9p7PtqzMPY5FoDt0db56xDC2LWqzv929SyYS/I/vL1B3fb330L35p8R'
            b'K865OxDv3gAaMpJ33FRrM0RmB+QIeR4OBLv3tN/E4FzPoDoPYc7HKzk4ELv6fmpKA1DHAKtI'
            b'hhnks6raQkAH23A0m5N49s6gTq4Vk6wiCEaIpqKlqCXn2bHvh5Qy5pQ//fj9i9OllBQjLJfc'
            b'TzeGA1DPq6NHpiqzocyNr0RoB+s9d0FAlUmphPm3jaaa2uF5hR8r6extsJZ0fswW3xzn4JP/'
            b'SM0R50UzfHOQN+a4M/pDg0YAq2vw5uU7E6z39zBs9Z+7Drfv34AR9kfm/XZzb2R7t2p1hDgS'
            b'GAGS7R6fbaLOXWHveK7GwMyymgtlAADzGMM3f4IqN3snPA4AVOea2f4qMECqHxMRfahtaoJI'
            b'wdcRnagmVK+3N01SsxwDETIzEwFAlaA1MQTKJTnnUk7s3NHx8v7+Ts2mcfPkvP35Jx8hlRh4'
            b'CW4oD8FjkcTLo/PKLQTA2uFT/ZYcEKp0LkCp2SzVUpPfaoY7NOvNoh4ayqE9fS/1PtgAHhrc'
            b'oVG+dcAfsa1acn7jIQ5ZXz+6c0TCPWQKu2HSb+pI8Aaj31U8f8Rd0Vv3Dz/pzpoZwADeOCc4'
            b'fCFUxjUjMqKnnSXZzFB4Myqsys3SrvJxeOEx8x5/R0SpUgeiWvcnRPWwzruKsgOAY+d9YHZM'
            b'bFphprqPIUQwRTWpIQhnsKjKJ9QDlxijaGEiH7ya5ZSWi6Z/uPzwg3dOT44Ii8CgNjqGbb/h'
            b'1fG5VbwJjJEcO3beOSel1AYUqMRBNVOpLIZqHrv0gnfwHNgP8m44wDnfuh1a1X4V64v2S/XW'
            b'0X7MsJBwtxtEqLnUDLRpze932B/u/AhUCR4Aq80Zs9+qL8Q3b4d3yjN4kF/VRG1vLvv3/OYR'
            b'IJ5Tut3SAhEg1jzNkJAYySERIiNUpWKeLzkEZjbAvadHettj1f/ryTd4c5FXk6rfEYwJidk5'
            b'Nt1NRpPDLRprUeLZj+58HqooOVKzOpi9ml3JKaWEBGaWSwKAVNKj8/NXr14dL9vN/SWDPX36'
            b'eLH4//r61mY5chw7PMjMet2XXj2e6emZceyGvf//l2z4qzccnrHXPf2QWtK9VZUkAfgDSCar'
            b'6qpTCkWpMiuTSYIH4AEIbI6n30TOpRzNcqA1G5iDSk20N5IOV9jzGhKsazoz6xeOP7kCpJFl'
            b'wEbQo6/aXqPa+8+tkfvo4qIXD+qXvdpIF79uxiEEpxjaBeyqbzTp6Ca8p29SGm7evjGE+iKM'
            b'aACrTBjV0puI5JQsGNUV7eWEhPFdfGgup1Y/2yJI0V1AHi6AiF7wx1M5+hozxuhr1ZwLADh9'
            b'yhQQ1NjXyCyCRIkIzbIBACHWKguMiCGEZTkVFWY0su1mk1L6+PG3P7zZ/o9//58//PCnx7f/'
            b'fd48LC9fU5H7hwd+fPO+vxoCMXOIEwfqNdfAwPcgIhAh1/SZegEzANDksvp6X4UZGo5v814X'
            b'YtFdEzBI8CgoBA0qoKvCtmCsBSfJx72KPlRIQv8DZBX4ailQRK90j11TXmFSe6kOWkzI9YP7'
            b'6dD/RaTg4c5G5NYLIfsOOPD1JwAhd1XoKgCJAcA39UNrercXvVVMkZARQL3ir7uqaoEgVJVS'
            b'sqmiYYjRnUXYttSSoaf2CyEgklXNyaqWS/HoFkd4MFMR8SqhoGaqpoiATPv9zje47eadiRXN'
            b'7//w4f3T06JnQNlMW356977xeYaEgSPHGEJwwaogNKyePJDG7FqwXN/3VcaVSI3I5DDuWv/K'
            b'8DKzFvcyilrFQriEohGE2n9XqONWi7APBjSsasLKowzjKpdYPUJAthptF1MFqzXW36vOFiOG'
            b'KoJYxcVtKSCHMxjuA+CqL65d5EkiLgWr376ZszX1MQ3RVwA99xC7AKWUVAUA/J5OR1cTrIjn'
            b'IW+BNHXdpqqlZESvYcYAoCJFBFSI4fn5OcYAqJ7wIkt59/adAZ6+Lg+Pb3799PHx7eNf/+XP'
            b'CpkiLiXz/f0jAqqaFAXEedpMYQIzJvbsENYiCypNbl7SnfzlewFITwsBLfyhx2yNGhCbUlMv'
            b'Nzq4jPrglJK7+dWWBdZyMV6IWr1ha19l3eq2MACPhAFTMy+v5dyVibm97k5Ng9Wygkq3YrfJ'
            b'iNjMk1XQNStG7LndDdCAzAcEAJAUSA3UOT1DREdVJzjYy/F4xmw15QtTnaDSSu6rIQ7Rbayu'
            b'nacQtaipxhCQSEQQIIZQR8oRBQGbCgHF08tRStluNtvNRkU8k28dl8AcggHkUgwgzpOnCpni'
            b'hGDn04mItvOU0jLPc0pLyZkDM7OaAejd3UOM+yUrRX4+fv3zX79/eHpKsCxS+P7hjYOFmgKi'
            b'R4YiUgjRH97+qYczDZ1u6PLR10ejTHT+0y5JdjOrM7KhyAAk9UNfFnSJvAIqWCkDHO/gdlK7'
            b'ZBXceg10oK0aE+pmRqyYskIUAPj28d9DLGg2FiICsuEa24hYs2D19tiIb9VxsQY2NlOLuvHu'
            b'jbVLeHZwYk/X3pKkSTMt8CLDKjHHUrJXG5nneb/fe1lG1xieT6ZPYFWNMaiKqRKHKQQiFMki'
            b'XhOoAFilokDnaZrm7bKAESvo/dP9jz//+K//9i+fnz/+9POvvLu7825VNVBg8nQVMYQ4vOog'
            b'HM2567DUUy1eCtbalV0y/HBxqdmbYTTL+gVrR39rATGMLjRKaTgFhEBtg+sFg4C1Cj1R27/v'
            b'smRoDat8ldSsbCSi4H4PxFXqoJrnjbKqzBYBAhIbNlOxCaWt7SdENEKvFsZEzuOuM8MtsOak'
            b'd06LG9tpjUesndOMGCLyIXG0ddPICXpTMPXM+Qsx7/c7T494zou1Dhs4I41zBMO0nBFxv9si'
            b'4nI+iZScszU4FKm5TInjPN8fz2divn/z8L/+/h9/+dsPHPD5+MKb3QGgMaAACBhicHeEEz2I'
            b'vpCqGtq6J26o+mctrGWMTeiStM62wcaCtv3wRldeWF19Jg0jusoWEdUaknAdYYGNOehn22yu'
            b'874tEOvTeuhzlyCq9Ob43PVFRuZ9FThEJL5CN7tQ3eSSX08hBA7cAAwHlOp0g6dq7B4wasug'
            b'3ofQwo57y3qPEWFO2TlPVc0leQrM7WZnbXNeF1MiYibREqe4pCWnNM8TE6Ulmef4BC8fpJ4C'
            b'DVCLwNv3f/j4+TNH2u3maebn0+e//e3Pm92Gt5stuKtGQQEIOYY4xYk5uBPAZzQYiFXB8pGw'
            b'lhy2Cfu1VPnL9zjBwbSvsjI6Crt2WIf68sABui6HrcJDxY6GFpXmpvYGvvTrOsuNngHPiENX'
            b'f52I8uut3rDintUUEQSIAPXKFZ8YPVONn3R+FRCMEag5i8AATEERMHCgLqBVOitiISLW3da1'
            b'k8FJAKTrb9aNX0Y1zN3RhUSrh5cIpZTlfDKweTPPm9mxp5RcVACBmOIUT6fjbrczhdPxhQk9'
            b'hb2nJFYtmouK+EuJliXl/e4uRjq9PMeIf/wvH/73P/7jv/3rXw93ez4c7pxStxb15nqQOfRB'
            b'dFHwmJ2aZqiVA7kVrHGKd5C/UoiIODqnO6fg748DJvXjVqQ6BoymWBdQaAFkV7/ldlB3I9O6'
            b'rYjw+hFrUMclPjU1fdFao7UF2EStWmO1KQPoEiIYY+jqwo1ZaX0LAM68wzCpvJ4Ph9XtUyek'
            b'CxljN/ah+rU4pVwkEyMhmxd0kTLVki1oLV203yfntNlsCKloQYUQOXJwr55qKSlrdWBCkZJT'
            b'UpO//OWHX3/9aYr05s398fnT0+Nht5356elN10hqgHVTIE/T3K0lrJvURAfj3V/ec+jCQDd0'
            b'awAG634ce+/WEYFHW4oGQnKUyFv0at/fCiL0W90KFmEgZOfkwG2karJDG3gcmTAPWelW1CDH'
            b'PCr8yqV5ZAcb4kqNKvYAHhzJryrS45ZbXy6sGYjRbay+fRkdrnyPpHllxvq9grhPnj3RbF9Z'
            b'e1oorMjrLNf5fMpSAGyKUwisJjkn5yIoRFMLzNMcTVRNIocQqJQC4oFAor7UFilSEOy7796n'
            b'fETUp8d7ZhE9HvY7LwCppSQxQ2QxLSq5FDNT98lD3WNvhKjYJ8rVcSUB2kLpxzitUc2NAHN1'
            b'arzGLlOJjLLVBXT83qyrrCZInnMLihu+puYJWw2k2pYIBhCat26FB+wmJqzcejtUoTes6cm6'
            b'HgRsFAYAQH0StYgxZ2yxrsWcjwc0jyQDrZuPQFWBkDwc1IXXzVkAdyz53Ja1x9BQCdkAANkg'
            b'exbOYrLZbAxhWZZlOU/T7CTF+Zye3r09bA8cYyllOZ1zTqWkx8fH5+fnw26/3+81l+NLEgLi'
            b'GZApbsKcsWST5L1OgKrpnz/+/XA4nE4vjFYEfvnx08sPZ97fPyKRGpSiahTnTZx2isxxIuY4'
            b'TcRcTLIUBUDGFiaF3XJv8sEjMq8jPcbZIBqAqIqIWwkjvPkdK0oSEXv0TiWWpN3BlxRO2ppB'
            b'ZyU68vmHGnai9a+32QwMhLhO8VxykQwIHLhGbjRzza204S90gTUEIGwsVfuXWuZBABP3vXp+'
            b'LyYMAAjqtb6YscZXuISZgQIhoMIa6tVMQzCnzxtXbwbETByIGYkNEAg5BGImZo7Bd0sjEgVm'
            b'DhSY0ESllOyIpVpz5U8xLufT+XgiwqfHp/u7Oyn5y28fI4NoYcYYJw4hJ81FQ4zzvFODJMW0'
            b'LoC1iEqiSEnS4e6wv9udzqfd4TDN219++RIaPHiCFOyOsJSyh18wMwZGZSumalZqiZURWn7n'
            b'6OExXaW6RT9qt/HzFYB1DBuFdfzJiFhjY2wg2WHItRRCcMFC5X5nItKbOzjqWJErZdpf5OZd'
            b'FQAB+FJTAwAQoDVbbj1bIVkB2/ZtuugTRFTfJ9m2SCGqiatxqiGAYNpdjeabXRDQTExRVC0Q'
            b'6bARC9EQGQCcJn0RAICSZLfb7Tbb7//4p3/+8v/2+y0APD9/iWF7//h4PJ4/ffr0eH+gOM3T'
            b'DkQRNKm4p9MUVCClNE0TcywZz6dznFo+CX+TzoQigNct0hjZa1ATC9aULTbEvK+/HRTcGPTX'
            b'B2Ds7maW1a7vvyUa/UKvH6MUfkuk+pUjfDqAOfHrga5exR4A6s6iQQ0OwrK6kkYzsW1hv1Du'
            b'V6/ZZmn1mVzbi3ZtTXpTvYu5tq0Sy25cI6JpYSRtOA3goRo1iNHpVlmXIB6Hqe3vSpScz2cA'
            b'UD2XL+l0Ot3f3z89Pd3d74u9fXn5mr583e12NJH7Ufb7PSJO0wS7HaOCZS2LG5qS1Qqcn5eZ'
            b'N/ObLSq/fDltNptgZp1GV0PQolqIakpHRyeklUkPRO5t71hyNeQ4JHEYBcsut3NddPEABr6B'
            b'tg9k/zwi08UPh2/GAe6geNVCs75Vev1Vv/hWaq+Qcvx+lOCrp7z6dr0fWld4TnKG4dQ48cxq'
            b'/EKfcv3VpNWk7cKqQz/7qUp7ii/3GKDvH66N8XWVqp6Xo34uZpby+f1371XLy/NZVVM+SzGi'
            b'8PT0cHp5maaJwdTylKeUpjBFlpJVStHj8zJNmSESRskGM/Nu/wCVSfdgPeRaOjiGGCopAgAA'
            b'RSXnNIfYVi1r6703+ps79YCNHe3TcZyyo5Bd9f74k953Omw4+53xu/rsNx9Q2bv+2t5/dXEw'
            b'CgV0d6SZea7USmZWYwgvD6KAOJiPw+rVzMA84NN/yAgwkhpOSUkzEp1u710XwoTYt21CDflt'
            b'wS3WcvmRm1/MWgozB568mlrndRu/4J9FVXJO5/OJ0Hbb7WazSynlIrvddp7mlBIhhsCEIJK1'
            b'iJkHACooEDGIAdLT/VOIczot07zl/eHBakrZajwRYSDezDNzdEbE+V9RdcFSk1biYg0ixdHn'
            b'1TDAzamrket019UMuxVBeO24lqcb4OxriNs7VBq1RQyM14/yhJey8mozer6TsVW08meM35B4'
            b'M89X3wO7PRhwfX3/0Nz/0M+2jlmTAgOuzo+rfZpNukmKMYcYI1OAFsHBzO7zsebDRUQn0Z6f'
            b'n0UkztNms53jbAgp5ZTSFJkZCbBtIAPJJecEVklqLTJN8xxnEWHiUPOVmBuWVopqEQ0KoB7x'
            b'540coxWsmVl4qenGHuyi00F7tMRV1X2FvY9GzXI12Ldjc/vf28NujPf+aGZ0C2Y0Fq/spNsX'
            b'gUux6y91JYteQ2hc7ULlxvx25OqhS63bRoGYmY1aInlPEVmZB6iLQjUwFRhzZ4ARFQRVmWkm'
            b'BAiEBKrY5jOEEJhj3xSOwJ5rMqXFDEWkmV/ePk4p/fLLL8uS33/4bp635/M55eRSS0QYcJ5n'
            b'MiW05fiCQISiqoSU0/Lbp48P93chRMmy7mio/QiiKrX+mxSkCQetBEBeYvAKh3Aw2K+G7SKT'
            b'XwAADWJJREFUn4dMRt1QG4d/tNWs8V5XmgUu9y2OUnVBbQyN6EW8+pCLiGpVAX5NXyp2lT1K'
            b'1dXEuDp7ZfMNP7neZTRe1jVgg59QpOZ7CiEYYd+KWG+CF3PVzMwKDGtnVdXiOVfjCHjeclX1'
            b'hGyIKAJ9FrnqBE+7j+Z1SQzEc15M07Qsy//9P/+4f3h89+5D3MyfP3/exAkRKeBkG/bg6Tg1'
            b'vBCiUIqcz0ePjxAR3t899cUQKiBADJFDAIAQIodoUCOEvH5FSQkRCKsH1FqMg9kYKgNd8aec'
            b'vZgRDET8OB6j4utxWpddaaNV2zuuYszl4PXrR6kdPzPXUA6rm2Ladre24avd1WGGpmlmDuNl'
            b'/YJ+B/eA+QVOr+iw68mf7mxWlyesdVzVN2zV1zFDAxx6ybSHIKDb7FIEzAg9j5yKiBt67hFh'
            b'r0IKqCIp55TyFGfEWhvbakgCImKoTqGayQwRPYQBDFRqwYYiknMKTA/3dynVgsUxxBi4lJxS'
            b'BhWzMkX28tglpxDCH7778Ntvn/hw/wSNswF1oxsICZzgQQJEpmBMUiSlBZ2ptnXpF6rvfR3a'
            b'0RvdBaiLGrXA1Ffn9O2pUTHBJVzBgFI3Kmk19sfVZY90ePW4bRW9xp+N73VlEY4fxt8ijG0Y'
            b'Xod4BGZs3sk+hYiq/6c9a+3Gsa2OBeOKx33hhOwRA4jWpLxmOQQAxMqtIiI6yevD3qoaOX7m'
            b'nA+HAwCUkgFhmuMUppzKy+klpxfTYqZEmHMJgQ+H/bKc+fDwxnsbsfKyAEZIUhTqLnYOISKT'
            b'iOacWmGBCwud2h43aHRR1xSjKTNC0fi5j8QoNKP5ggNPdisN42DfnhqHDV4THT8uhGCMtqi7'
            b'WhvtDn0JgO4ZdN/fGnxaoW54qNEgSeNngMqM4mCFQfU2DFRf9VzW1+wrUfOx8BQ/hGCe3gt8'
            b'byAxEVNA8OLt4uKoVmvPuC3Tb+8o7vLmvS3qkcmlSMk5AVic4nazJSKohWkMQU/HLwpCxCHG'
            b'lJOB7fZbYqqZOZxFrbQBIJiULJ5yBQMDrLNfh004XWg6PNjl4Qz9aD/dDvMV5Hxr4G3cnNOu'
            b'txs+bFB5fHWr3xHNfn3/eZ/6cslNXCHiq7eCyykEMMr9K1A9Wpn9573O4/ovXlNuTXDNQcXM'
            b'sPHsHhyAiEq2JJWiHBCBx8EaO4OIPIspFDGzogqi0jIti8iyLB8+fIjsuMgxzPs9lLx83u7t'
            b'KBg4xphSEbHTaXn79i1v7h47hUWgZooARCyiPk9DnKbNhmI0NSkiJXmkeNd3DbTHINe1g7pP'
            b'kNo+REe4/vM+3r2nbtUotmw2V2IEAHxpdfWjhz6P49eG+ZW/zDyYVh0pVosKqwMP8dIUq9sS'
            b'GxF48SK6rmmY4xVWtZiI9XoE6MhUuahRQK1t928BmFddVokDAFgVNBBRKcWRzCe7D5NvpuiG'
            b'IxEFnuIUGdGDns0f2dg7D2g+nk4l5/1u9/j4SIjn03k5n87LAkgAWETVIMbp/v6Bd3ePogpq'
            b'DOhbvRiRvaKcqiEQxzhveJrUUEVyOo+qEFavM3bQ6jDr/Xc7j6Gttjrk9ONq4n7r+/6Zvo1A'
            b'cIN/I+BdHSNcwQDG43Lh1ePqbIc6RPRe8s9csyqMs+X3IoJqr9JqqPk3nq+mb97B7ucYUgfY'
            b'RdsAAD1YuZH43Punvqm2vE5IgWoS865xfYu1Q6CZiYqZMREBhRjPy+n0csxZcipeZVDEtpsd'
            b'3z2+NTOva+Co2oxG9tIFHKZps6EQfFfJcjr6mroTaw5CLYIAoOnv3u7+kn3k7NLAv5l7cPU9'
            b'3jDvayfeKNNBvvVbd7s9RkTsLTFrdR9ujtG4HuWjRltgcK3XRYR5RFAaAf5WTPudGVtaplHa'
            b'6mqxBxKCma3hzmZSyti9XvOllKwqzr+LSA0EMgJDVXAGSVUCERJ6HccQCdETLIiZbjbzdrsD'
            b'gNPx/HI8quo8TfO0eT4ezymfl4wUkMM5LZ4Bka2xsN4X/tnTcWfVWIqIoLpLA+o43hgKo83R'
            b'Z3/nF8be9w++W/dKqn7/eBVvukBQY72h2XN1Kg+eJWtmn4/Wxb/YI4MRATxtkq5P9Jrh1Aop'
            b'KiJXgxPN9z07BYsUyDeyEJqhgqBRLa7sjCdh3xMNuGZ1VjPfPY0AisAem1ULgIKCMaAhlFLE'
            b'1ESBkFskBRGJqoOQiEixUkpnKrxMunudsVFcMQIRMQUAQKxVusGgSGbGGOcYUDQys0MOI0ku'
            b'hRdCJFRZTl8kn5+//O2//uXw8+F4PJ5OJw8nPp/Py7Lw4+OHGgEOUERUDYnjNImAYd0chxym'
            b'eSYmBMhp8fywTqt4NSxPYN+nyOgrBDTimtXCgw8949SQLAP6fxsEN4eMVWcZAsRQM7b2+e7L'
            b'cFGF0cDyGeJjTuSbYbAHbgAAsrrORzQFRQRDRWTfr6wmAKZgRIEDxYjMYiYKCoYciBnQ9+Ew'
            b'ECIHZM/XgIAMSAqAzIGDIoJ6DfhIIaroOeWSxZAQsJiaqhEGZgzMREZoagJmAApGREtOaurh'
            b'VsUUACgGMwMmZgYm727mKcRJ1eqO2MarmULJRc0AcJrmzWaLSKWIqsUYG2VY2Qf20tNlEc0c'
            b'CRBzKSGE/X5PiMv5DCaoGU0mhpmBrGg+5nRa8vL+u3ccwvF0NNDzclLTaY78+PRBVdFDk1V0'
            b'9QxaMVUBJZinTZwjI6tJPi3aBEtVfRHrZSCu7Guq95GOWCPfAzfqCZqJOmqifpmbCJ2Y7tS/'
            b'NTAbb3v7uX/Q0fKrQu2QhNCCZGrIXlU0HpbS415qqLvf1VvQQAcAwLcfi5rXK1a1GmmE4GDp'
            b'lhOi1/lkX+t5QUF/rl+fcjYzActSimez9U01bvw1E7A3oHUvjYaXm0TaMgDO8+yFd1JKvZNV'
            b'FVq4imjxdEZZcpHcPU/EoKlwgAkJtWjJVhKjRubPXz+fU3r37u39/d0vv/xcSr7b71NO/Pjm'
            b'Q22ambZGOOEppqWoAsQ4x2liDgqaz4to6QRpZUdU+6K6c1pVB3kCJ0+qQozu6xZx5qfDFpgn'
            b'DnzF4dgV6KgBx//eShUO5ks/W3scLjTyreTdiHvr3Esi9IrmHa4Zo2rXIFscqLjxrA9tTyuM'
            b'PRuZ+0+x6vowbMu57o3m0gaAHlJhPb8rgtcLYOYmWFZKLT/vJZU9Z4e/H5iWklP2VJcVO7a7'
            b'zcuXryFSQFItOWeVQgiAxlN8OR5Pp+OH9x++/9OfPn36+M///HG/3/Pj04VgddkHQDVTMUOM'
            b'cZ7mOYSooFrEBcuPRrub+/Mbm8DduIkxjAMJbVV8i2FtNUArejURsdciSEeZe/W/r16v3/75'
            b'7cXYvHtdGvpl3W7rsdF+QYfUqxnCr6UIgMusO/UsISL66s9DX0KjbPyhnbJpD+1bO+udemea'
            b'WZyi+3Ncdn0ZMc9zSqlrAM+1FmOMU2BCVckll1JSysUV4m77/OVrICTAUpKKEICppJxeji/v'
            b'3j2lZfn068enh4cP7z6UlJ6/PvPD43tradJdyqGCTVAwh8kuWIaGaqVk9wy6YHnCCReI1gvr'
            b'+2OrQjAKCg1ha9CdqfWaNQBLhxQPMKwJxoNunI9XgjLihAvW7TUwQN2VzPl44ZV/5nLr1aXA'
            b'1dpgntiiV7Pqj+g+ier7E+k3r7q9CWvOWUxdqvyyaZqs5cUYxL1nObg4asu4LiQ9/ZqITNO8'
            b'3W4v5R7a2PFm3nhmU1PLpaSUmCjGYKohkORyPh3NLAYG0yUtS1pEyhyntJx+/umn/Xb3/R+/'
            b'D4H5cP/GrO6Ha1uzvR9d/WMXLOYACKiWSwLDcfZAWyb26eXvFkJYlkVaqrk+QiEER+MrcQEA'
            b'ROqrG2ga58o5jYNiwst4m1Em8FL71E4cVNsVpN2iFyL27FRXj+jycSPWqx7syDG2xw9sW5hG'
            b'LtB/6KuNFnFwodzH566CCPjq012+ixRHo35P72FHxDbza1AJMW7mua2P0QeOEAHs7nAIjDml'
            b'4/EZpUxzYCKRtN1OKZ2Xl6OagcjnL1/Q7Icf/sr7wxMAcO0I68reEcsUgDCEKU4TERsYGSzp'
            b'rGKdRyAiVQ0h0hCP0Vf7y3LWIRaq92z/0i4JJ6gk+EXWmlGwrublFYD1Hu9yg5c6safl6Kf6'
            b'wF+JYMMVu3pQFxocWLT+7qVIl7ycc8/LPVIevQH9vXwSet1AaKTd3d3dvN04Vu12u2maXH/1'
            b'd2wdCDD4Ou3S7KtJFob4MBdoF7WqcLQnGiEfPw4B0ZMwkYGKlPvDXQyEBjkvjDBvJkLM+Vxy'
            b'+v77P55env/xj79PYd5s5uPzKeclaItP6jDTOrSmaRgnh3sVx2nXmztNU38ZtwpbnvtVnfn3'
            b'1Hw78JrdPX4zCkqX1AHbEDtdsTIda6sugKq7j/Cbj7tqyVUD+j39Al9e9anSB+np8a2/b855'
            b'WRZP6kJELy8v2GTaWmAjIk7T5DFFzLzdbpn5tJxFZLfbvXv3ThF++uknM7u7uzOzl5eX0SYb'
            b'mzdO0f4gIooxdmjs0uycU4xxnmciKlE7rZiXZZpCCGGaJikGAEs6lZJyStN+Puz3JZ9lOYfA'
            b'loukvDnM//zxPwHou/cfvn59Tinf3T18+vXj/wehjB8Hf7GHmwAAAABJRU5ErkJggg==')

        self.david_picture = wx.BitmapButton(
            self, wx.ID_ANY, david_olsen.GetBitmap()
        )
        self.david_picture.SetSize(self.david_picture.GetBestSize())
        self.david_header = wxStaticText(self, wx.ID_ANY, "David Olsen (1982-2024)")
        eulogy:str = _(EULOGY_TEXT)
        if system() == "Darwin":
            # MacOS does not wrap labels around, so we need do it ourselves
            splitted = eulogy.split("\n")
            lines = []
            LINELEN = 45
            for l in splitted:
                words = l.split()
                start = ""
                for w in words:
                    if len(w) + len(start) > LINELEN:
                        if start:
                            lines.append(start)
                            start = w
                        else:
                            # Word is too long
                            lines.append(w)
                            start = ""
                    else:
                        if start:
                            start += f" {w}"
                        else:
                            start = w
                if start:
                    lines.append(start)
            eulogy = "\n".join(lines)
        self.david_text = wxStaticText(
            self,
            wx.ID_ANY,
            eulogy,
        )

        self.__do_layout()
        self.david_text.Bind(wx.EVT_LEFT_DCLICK, self.on_eulogy)


    def __do_layout(self):
        fontsize = 16 if system() == "Darwin" else 10

        self.david_header.SetFont(
            wx.Font(
                8,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.david_text.SetFont(
            wx.Font(
                fontsize,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                0,
                "Segoe UI",
            )
        )
        self.david_text.SetMaxSize(dip_size(self, 400, -1))
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        sizer_left = wx.BoxSizer(wx.VERTICAL)
        sizer_right = wx.BoxSizer(wx.VERTICAL)
        sizer_left.Add(self.david_picture, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_left.AddSpacer(5)
        sizer_left.Add(self.david_header, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_right.Add(self.david_text, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_left, 0, 0, 0)
        sizer_main.AddSpacer(5)
        sizer_main.Add(sizer_right, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_main)
        self.Layout()
        # end wxGlade
    
    def on_eulogy(self, event):
        import webbrowser
        url = "https://github.com/meerk40t/meerk40t/wiki/History:-Major-Version-History,-Changes,-and-Reasons"
        webbrowser.open(url, new=0, autoraise=True)

class InformationPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.mk_version = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.config_path = TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.os_version = TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_READONLY | wx.TE_MULTILINE
        )
        self.os_version.SetMinSize(wx.Size(-1, 5 * 25))
        self.info_btn = wxButton(self, wx.ID_ANY, _("Copy to Clipboard"))
        self.Bind(wx.EVT_BUTTON, self.copy_debug_info, self.info_btn)
        self.update_btn = wxButton(self, wx.ID_ANY, _("Check for Updates"))
        self.Bind(wx.EVT_BUTTON, self.check_for_updates, self.update_btn)
        self.__set_properties()
        self.__do_layout()
        self.SetupScrolling()

    def __set_properties(self):
        # Fill the content...
        import os
        import platform
        import socket

        uname = platform.uname()
        info = ""
        info += f"System: {uname.system}" + "\n"
        info += f"Node Name: {uname.node}" + "\n"
        info += f"Release: {uname.release}" + "\n"
        info += f"Version: {uname.version}" + "\n"
        info += f"Machine: {uname.machine}" + "\n"
        info += f"Processor: {uname.processor}" + "\n"
        info += f"Theme: {self.context.themes.theme}, Darkmode: {self.context.themes.dark}\n"
        try:
            info += f"Ip-Address: {socket.gethostbyname(socket.gethostname())}"
        except socket.gaierror:
            info += "Ip-Address: localhost"
        self.os_version.SetValue(info)

        info = f"{APPLICATION_NAME} v{APPLICATION_VERSION}"
        self.mk_version.SetValue(info)
        info = os.path.dirname(self.context.elements.op_data._config_file)
        # info = self.context.kernel.current_directory
        self.config_path.SetValue(info)

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)

        sizer_mk = StaticBoxSizer(self, wx.ID_ANY, "MeerK40t", wx.HORIZONTAL)
        sizer_mk.Add(self.mk_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_mk, 0, wx.EXPAND, 0)

        sizer_cfg = StaticBoxSizer(
            self, wx.ID_ANY, _("Configuration-Path"), wx.HORIZONTAL
        )
        sizer_cfg.Add(self.config_path, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_cfg, 0, wx.EXPAND, 0)

        sizer_os = StaticBoxSizer(self, wx.ID_ANY, "OS", wx.HORIZONTAL)
        sizer_os.Add(self.os_version, 1, wx.EXPAND, 0)
        sizer_main.Add(sizer_os, 1, wx.EXPAND, 0)  # This one may grow

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.info_btn, 2, wx.EXPAND, 0)
        button_sizer.Add(self.update_btn, 1, wx.EXPAND, 0)
        sizer_main.Add(button_sizer, 0, wx.EXPAND, 0)

        sizer_main.Layout()
        self.SetSizer(sizer_main)

    def check_for_updates(self, event):
        self.context.setting(str, "last_update_check", None)
        now = datetime.date.today()
        if self.context.update_check == 2:
            command = "check_for_updates --beta --verbosity 3\n"
        else:
            command = "check_for_updates --verbosity 3\n"
        self.context(command)
        self.context.last_update_check = now.toordinal()

    def copy_debug_info(self, event):
        if wx.TheClipboard.Open():
            msg = ""
            msg += self.mk_version.GetValue() + "\n"
            msg += self.config_path.GetValue() + "\n"
            msg += self.os_version.GetValue() + "\n"
            # print (msg)
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
        else:
            # print ("couldn't access clipboard")
            wx.Bell()


class ComponentPanel(ScrolledPanel):
    def __init__(self, *args, context=None, **kwds):
        # begin wxGlade: MovePanel.__init__
        kwds["style"] = kwds.get("style", 0) | wx.TAB_TRAVERSAL
        ScrolledPanel.__init__(self, *args, **kwds)
        self.context = context
        self.context.themes.set_window_colors(self)
        self.list_preview = wxListCtrl(
            self,
            wx.ID_ANY,
            style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES | wx.LC_SINGLE_SEL,
            context=self.context, list_name="list_about",
        )
        self.info_btn = wxButton(self, wx.ID_ANY, _("Copy to Clipboard"))
        self.Bind(wx.EVT_BUTTON, self.copy_debug_info, self.info_btn)
        self.content = list()
        self.get_components()
        self.__set_properties()
        self.__do_layout()
        self.SetupScrolling()

    def __set_properties(self):
        self.list_preview.AppendColumn(_("#"), format=wx.LIST_FORMAT_LEFT, width=55)
        self.list_preview.AppendColumn(
            _("Component"), format=wx.LIST_FORMAT_LEFT, width=100
        )
        self.list_preview.AppendColumn(
            _("Version"), format=wx.LIST_FORMAT_LEFT, width=120
        )
        self.list_preview.AppendColumn(
            _("Status"), format=wx.LIST_FORMAT_LEFT, width=120
        )
        self.list_preview.AppendColumn(
            _("Source"), format=wx.LIST_FORMAT_LEFT, width=200
        )
        for idx, entry in enumerate(self.content):
            list_id = self.list_preview.InsertItem(
                self.list_preview.GetItemCount(), f"#{idx + 1}"
            )
            self.list_preview.SetItem(list_id, 1, entry[0])
            self.list_preview.SetItem(list_id, 2, entry[1])
            self.list_preview.SetItem(list_id, 3, entry[2])
            self.list_preview.SetItem(list_id, 4, entry[3])
        self.list_preview.resize_columns()

    def __do_layout(self):
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.list_preview, 1, wx.EXPAND, 0)
        sizer_main.Add(self.info_btn, 0, 0, 0)
        sizer_main.Layout()
        self.SetSizer(sizer_main)

    def get_components(self):
        def get_python():
            import platform

            entry = [
                "Python",
                platform.python_version(),
                _("Present"),
                "https://www.python.org",
            ]
            self.content.append(entry)

        def get_wxp():
            entry = ["wxPython", "", "", "https://www.wxpython.org"]
            info = "??"
            status = _("Old")
            try:
                info = wx.version()
                status = _("Present")
            except:
                pass
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_numpy():
            entry = ["numpy", "", "", "https://numpy.org/"]
            try:
                import numpy as np

                try:
                    info = np.version.short_version
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pillow():
            entry = ["pillow", "", "", "https://pillow.readthedocs.io/en/stable/"]
            try:
                import PIL

                try:
                    info = PIL.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_potrace():
            entry = ["potracer", "", "", "https://pypi.org/project/potracer/"]
            status = _("Present (slow)")
            info = "0.05 (internal)"
            try:
                import potrace

                # for e in vars(potrace):
                #     print (f"var {e} - {getattr(potrace, e)}")
                if hasattr(potrace, "potracelib_version"):
                    status = _("Present (fast)")
                    entry[0] = "pypotrace"
                    entry[3] = "https://pypi.org/project/pypotrace/"
                    info = potrace.potracelib_version()
                if not hasattr(potrace, "Bitmap"):
                    status = _("Faulty, please report")
            except ImportError:
                pass
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_vtrace():
            entry = ["vtracer", "", "", "https://pypi.org/project/vtracer/"]
            try:
                import vtracer

                # for e in vars(vtracer):
                #     print (f"var {e} - {getattr(vtracer, e)}")
                try:
                    info = vtracer.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_ezdxf():
            entry = ["ezdxf", "", "", "https://ezdxf.readthedocs.io/en/stable/"]
            try:
                import ezdxf

                try:
                    info = ezdxf.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pyusb():
            entry = ["pyusb", "", "", "https://pypi.org/project/pyusb/"]
            try:
                import usb

                try:
                    info = usb.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_pyserial():
            entry = ["pyserial", "", "", "https://pypi.org/project/pyserial/"]
            try:
                import serial

                try:
                    info = serial.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_opencv():
            entry = ["opencv", "", "", "https://opencv.org/"]
            try:
                import cv2

                try:
                    info = cv2.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_barcode():
            entry = [
                "barcode-plugin",
                "",
                "",
                "https://pypi.org/project/meerk40t-barcodes/",
            ]
            has_barcodes = False
            try:
                import barcodes as mk

                has_barcodes = True
                if hasattr(mk, "version"):
                    info = mk.version
                elif hasattr(mk, "__version__"):
                    info = mk.__version__
                else:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)
            if has_barcodes:
                try:
                    import qrcode

                    info = "??"
                    try:
                        info = qrcode.__version__
                    except AttributeError:
                        pass
                    entry = (
                        "qrcode",
                        info,
                        _("Present"),
                        "https://github.com/lincolnloop/python-qrcode",
                    )
                    self.content.append(entry)
                except ImportError:
                    pass
                try:
                    import barcode

                    info = "??"
                    try:
                        info = barcode.version
                    except AttributeError:
                        pass
                    entry = (
                        "barcodes",
                        info,
                        _("Present"),
                        "https://github.com/WhyNotHugo/python-barcode",
                    )
                    self.content.append(entry)
                except ImportError:
                    pass

        def get_clipper():
            entry = ["clipper", "", "", "https://pypi.org/project/pyclipr/"]
            try:
                import pyclipr

                try:
                    info = pyclipr.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except ImportError:
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        def get_numba():
            entry = ["numba", "", "", "https://numba.pydata.org/"]
            try:
                import numba

                try:
                    info = numba.__version__
                except AttributeError:
                    info = "??"
                status = _("Present")
            except (ImportError, AttributeError):
                info = "??"
                status = _("Missing")
            entry[1] = info
            entry[2] = status
            self.content.append(entry)

        self.content.clear()
        get_python()
        get_wxp()
        get_numpy()
        get_pillow()
        get_potrace()
        get_vtrace()
        get_ezdxf()
        get_pyusb()
        get_pyserial()
        get_opencv()
        get_barcode()
        get_clipper()
        get_numba()

    def copy_debug_info(self, event):
        if wx.TheClipboard.Open():
            msg = ""
            for entry in self.content:
                msg += f"{entry[0]}: {entry[1]}, {entry[2]} \n"
            # print (msg)
            wx.TheClipboard.SetData(wx.TextDataObject(msg))
            wx.TheClipboard.Close()
        else:
            # print ("couldn't access clipboard")
            wx.Bell()

    def pane_show(self):
        self.list_preview.load_column_widths()

    def pane_hide(self):
        self.list_preview.save_column_widths()

class About(MWindow):
    def __init__(self, *args, **kwds):
        from platform import system as _sys

        super().__init__(
            480,
            360,
            *args,
            style=wx.CAPTION
            | wx.CLOSE_BOX
            | wx.FRAME_FLOAT_ON_PARENT
            | wx.TAB_TRAVERSAL
            | (wx.RESIZE_BORDER if system() != "Darwin" else 0),
            **kwds,
        )
        self.notebook_main = wx.aui.AuiNotebook(
            self,
            -1,
            style=wx.aui.AUI_NB_TAB_EXTERNAL_MOVE
            | wx.aui.AUI_NB_SCROLL_BUTTONS
            | wx.aui.AUI_NB_TAB_SPLIT
            | wx.aui.AUI_NB_TAB_MOVE,
        )
        self.window_context.themes.set_window_colors(self.notebook_main)
        bg_std = self.window_context.themes.get("win_bg")
        bg_active = self.window_context.themes.get("highlight")
        self.notebook_main.GetArtProvider().SetColour(bg_std)
        self.notebook_main.GetArtProvider().SetActiveColour(bg_active)

        self.sizer.Add(self.notebook_main, 1, wx.EXPAND, 0)

        self.panel_about = AboutPanel(self, wx.ID_ANY, context=self.context)
        self.panel_david = DavidPanel(self, wx.ID_ANY, context=self.context)
        self.panel_info = InformationPanel(self, wx.ID_ANY, context=self.context)
        self.panel_component = ComponentPanel(self, wx.ID_ANY, context=self.context)
        self.notebook_main.AddPage(self.panel_about, _("About"))
        self.notebook_main.AddPage(self.panel_david, _("In Memory of David Olsen"))
        self.notebook_main.AddPage(self.panel_info, _("System-Information"))
        self.notebook_main.AddPage(self.panel_component, _("MeerK40t-Components"))

        self.add_module_delegate(self.panel_about)
        self.add_module_delegate(self.panel_david)
        self.add_module_delegate(self.panel_info)
        self.add_module_delegate(self.panel_component)
        _icon = wx.NullIcon
        _icon.CopyFromBitmap(icon_about.GetBitmap())
        self.SetIcon(_icon)
        self.SetTitle(_("About"))

        name = self.context.kernel.name
        version = self.context.kernel.version
        self.SetTitle(_("About {name} v{version}").format(name=name, version=version))
        self.restore_aspect()
