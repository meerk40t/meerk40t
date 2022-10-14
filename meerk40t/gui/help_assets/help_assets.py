english_wordlist_howto = """
WordLists allow you to create text elements in your design which contain placeholder text that is replaced at burn time from this WordList. You can then burn several items with different text without having to change your design each time. 

A placeholder consists of a name inside curly brackets e.g. '{FIRSTNAME}'. You use the name in the WordList Editor to associate it with the placeholder and the placeholder will be replaced by the text you enter into the associated WordList Contents.

As an example of how this functionality would be used, imagine you want to create a set of dinner party seat reservation tags each with a different person's name. Having created the cut path for the name-tag outline e.g. a rectangle, use the Text drawing tool to create a Text element containing the following:
'This seat is reserved for {FIRSTNAME}'

Then you use this WordList editor to create one or more entries as follows:
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| firstname | Text |   0   |
	|-----------|------|-------|
Then click on the 'firstname' row and add several items to the Contents pane e.g.:
	Paul
	David
	Andy
Now when you execute the burn, you will get individual place tags which have different names on them e.g. 'This seat is reserved for Andy'.

You can use as many different placeholder names as you like in text fields in your design.

The 'Index' value in the WordList table indicates which entry in the Contents list will be used next, zero meaning the first entry. The index is automatically increased by one at the end of each burn.

But suppose for efficiency you now want to burn two seat reservation tags at the same time each having a different name from the same list. In this case, if the first tag use '{NAME#+0}' and in the second '{NAME#+1}' (note the plus sign). '{NAME#+0}' uses the current entry (pointed to by the Index value), '{NAME#+1}' uses the next entry after the current one etc. 

With the above usage, you can use e.g. '{NAME#+0}' as many times as you wish in your design. However, if you are only using the placeholder once in your design, then an alternative is to use '{NAME++}' which advances the Index each time the placeholder is used.

As an alternative to manually entering the wordlist values using this WordList Editor, you can use a standard comma-separated CSV file. The placeholder names are defined in standard CSV header line (the first line in the CSV file), and the contents are then taken from all the following lines. The easiest way to create a CSV file is using a spreadsheet e.g. Excel, however e.g. for ecommerce sites your website might automaticallycreate the CSV file from the orders placed online by customers. 

Entries loaded from a CSV file are shown as Type CSV, and you can set the Index values for all CSV entries at the same time.

Note: If your CSV doesn't have a header line, columns will be named 'column_1', 'column_2' etc.

The Wordlist also contains some special entries (which might be especially useful for calibration designs):
	* 'version'   - Meerk40t version
	* 'date'      - Date burn started
	* 'time'      - Time burn started
	* 'op_device' - Device you are burning on
	* 'op_speed'  - Speed of the current operation
	* 'op_power'  - PPI of the current operation
	* 'op_dpi'    - DPI of the current (raster) operation
	* 'op_passes' - Operation passes of the current operation

The placeholders for 'date' and 'time' can also contain formatting directives that allow you to format them according to your local conventions e.g.
	{date@%d.%m.%Y} - 31.12.2022
	{time@%H:%M} - 23:59

For a complete set of format-directives see: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

german_wordlist_howto = """
Ick Sprechen Kinen Duetch
"""


def asset(context, asset):
    language = context.language
    lang = "english"
    if language == 0:  # ("en", "English", wx.LANGUAGE_ENGLISH)
        lang = "english"
    if language == 1:  # ("it", "italiano", wx.LANGUAGE_ITALIAN),
        lang = "italian"
    if language == 2:  # ("fr", "français", wx.LANGUAGE_FRENCH),
        lang = "french"
    if language == 3:  # ("de", "Deutsch", wx.LANGUAGE_GERMAN),
        lang = "german"
    if language == 4:  # ("es", "español", wx.LANGUAGE_SPANISH),
        lang = "spanish"
    if language == 5:  # ("zh", "中文", wx.LANGUAGE_CHINESE),
        lang = "chinese"
    if language == 6:  # ("hu", "Magyar", wx.LANGUAGE_HUNGARIAN),
        lang = "hungarian"
    if language == 7:  # ("pt_PT", "português", wx.LANGUAGE_PORTUGUESE),
        lang = "portuguese"
    if language == 8:  # ("pt_BR", "português brasileiro", wx.LANGUAGE_PORTUGUESE_BRAZILIAN),
        lang = "portuguese_brazilian"
    if language == 9:  # ("ja", "日本", wx.LANGUAGE_JAPANESE),
        lang = "japanese"
    if language == 9:  # ("nl", "Nederlands", wx.LANGUAGE_DUTCH),
        lang = "dutch"
    try:
        return globals()[f"{lang}_{asset}"]
    except KeyError:
        try:
            return globals()["english" + asset]
        except KeyError as e:
            return ""
