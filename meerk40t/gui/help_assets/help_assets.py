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

But suppose for efficiency you now want to burn two seat reservation tags at the same time each having a different name from the same list. In this case, if the first tag use '{NAME#+0}' and in the second '{NAME#+1}' (note the plus sign). '{NAME}' or '{NAME#+0}' uses the current entry (pointed to by the Index value), '{NAME#+1}' uses the next entry after the current one etc.

With the above usage, you can use these values as many times as you wish in your design. To advance the index you need to click on the Prev / Next buttons in the toolbar.

As an alternative to manually entering the wordlist values using this WordList Editor, you can use a standard comma-separated CSV file. The placeholder names are defined in standard CSV header line (the first line in the CSV file), and the contents are then taken from all the following lines. The easiest way to create a CSV file is using a spreadsheet e.g. Excel, however e.g. for ecommerce sites your website might automatically create the CSV file from the orders placed online by customers.

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
Wortlisten erlauben es, innerhalb von Text-Elementen Platzhalter zu verwenden, die beim Brennvorgang durch Inhalte der Wortliste ersetzt werden.
So ist es möglich, bei jedem Brennvorgang andere Textinhalte zu verwenden, ohne dass dafür jedes mal das Design verändert werden müsste.

Ein Platzhalter besteht aus einem Namen in geschweiften Klammern (etwa '{VORNAME}'). Dieser Name wird im Wortlisten-Editor zusammen mit zugeordneten Texten definiert, so dass er anschließend im Design durch die 'richtigen' Inhalte ersetzt werden kann.

Kommen wir zu unserem Anwendungsfall: wir wollen eine Namensschild-Vorlage für eine Feier erstellen, die leicht wiederverwendbar ist. Erstellen wir also zunächst einen Rahmen (z.B. ein Rechteck) und platzieren mit dem Text-Tool ein Text-Element innerhalb dieses Rahmens. Den Text verändern wir zu:
'Hier sitzt {VORNAME}'

Mit dem Wortlist-Editor definieren wir nun diesen Platzhalter:
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| vorname   | Text |   0   |
	|-----------|------|-------|
Wir klicken auf diesen Eintrag in der linken Liste und fügen auf der rechten Seite mehrere passende Einträge hinzu:
	Antje
	David
	Oma

Wenn wir nun den Brennvorgang starten, erhalten wir individualisierte Platzkarten mit den einzelnen Namen aus der Wortliste, also etwa: 'Hier sitzt Antje'.

Wir können beliebig viele solcher Platzhalter definieren und verwenden.

Der 'Index' Wert in der Wortlist-Tabelle legt fest, welche der auf der rechten Seite angezeigten Einträge das nächste mal verwendet werden soll (wobei der Wert 0 den ersten Eintrag in der Liste meint).

Wir sind nicht beschränkt auf eine einmalige Verwendung eines Platzhalters (nützlich beispielsweise wenn man nicht nur ein Schild sondern gleich mehrere in einem Rutsch brennen will). Die Standardverwendung {VORNAME} nimmt den Wert an der Position #index der geladenen Liste, {VORNAME#+1} (beachte das #+1 am Ende) verwendet den nächsten Eintrag, {VORNAME#+2} den übernächsten usw.

Auf diese Weise können diese Werte beliebig häufig verwendet werden, der Index wird dadurch nicht weitergeschaltet. Mit den Knöpfen 'Vor' und 'Zurück' kann der Index weitergeschaltet werden.

Wir können einen ganzen Satz von Variablen (Wortliste genannt) definieren, der z.B. aus einer Standard Komma-separierten CSV-Datei eingelesen werden kann. Dann hätten wir nicht nur wenige Einträge für 'VORNAME', sondern vielleicht Hunderte davon. Welcher der Mehrfach-Einträge gerade aktiv ist entscheidet der sogenannte Index.

Der einfachste Weg solche Dateien zu erzeugen, ist das Verwenden einer Tabellenkalkulation wie Excel oder LibreCalc, sie kann aber auch anderen Quellen wie einer Webseite stammen, die solche Daten automatisch bei Kundenaufträgen anlegt.

Einträge die aus einer CSV-Datei stammen, werden mit der Typ 'CSV' gekennzeichnet, und der Index aller CSV-Einträge wird zur gleichen Zeit festgelegt.

Achtung: Hat die CSV-Datei keine Kopfzeile mit Spaltennamen, so werden die einzelnen Spalten 'column_1', 'column_2' etc. benannt werden.

Es gibt eine Reihe von vordefinierten Variablen, die Infos zum aktuellen Arbeitsgang (etwa {op_power}, {op_speed} u.a. - nützlich z.B. bei Kalibrier-Tests) oder Datums-Zeit-Infomationen liefern ({date}, {time})."
	* 'version'   - Meerk40t Version
	* 'date'      - Datum für den Start des Brennvorgangs
	* 'time'      - Zeit für den Start des Brennvorgangs
	* 'op_device' - Name des Geräts auf dem gelasert wird
	* 'op_speed'  - Geschwindigkeit des aktuellen Arbeitsvorgangs
	* 'op_power'  - Leistung des aktuellen Arbeitsvorgangs
	* 'op_dpi'    - DPI (Pixelauflösung) des aktuellen Arbeitsvorgangs
	* 'op_passes' - Anzahl der Durchläufe des aktuellen Arbeitsvorgangs

Die Platzhalter {date} und {time} können mit einem Format angegeben werden, so dass ihr Aussehen mit lokalen Standards übereinstimmt: z.B.
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59
Für eine komplette Liste der Format-Codes: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

italian_wordlist_howto = """
Variabili di testo consente di inserire elementi di testo in un progetto sostituendoli a dei “segnaposto”. Il testo viene sostituito al momento della lavorazione. È quindi possibile produrre più elementi con testi diversi senza dover modificare ogni volta il progetto.

Un segnaposto consiste in una parola all'interno di parentesi graffe, ad esempio '{FIRSTNAME}'. La parola viene associato al segnaposto presente in Gestione variabili di testo e il segnaposto viene sostituito dal testo inserito nel contenuto della variabile di testo associata.

Come esempio di utilizzo di questa funzionalità, immaginiamo di voler creare una serie di etichette per la prenotazione di posti a sedere ad una cena, ognuna con il nome di una persona diversa. Dopo aver creato il percorso di taglio per il contorno dell'etichetta, ad esempio un rettangolo, si utilizza lo strumento di disegno Testo per creare un elemento testo contenente quanto segue:

Questo posto è riservato a {INVITATO}.
Quindi si utilizza Gestione variabili di testo per creare una o più voci come segue:

	|-----------|------|-------|
	| Nome      | Tipo | Indice|
	|-----------|------|-------|
	| invitato  | Text | 0     |
	|-----------|------|-------|

Quindi selezionare la riga "invitato" e aggiungere i dati necessari nel pannello Contenuto, ad es:

	Paolo
	Davide
	Andy

Eseguendo la lavorazione si otterranno segnaposto individuali con nomi diversi, ad esempio 'Questo posto è riservato a Andy'.

È possibile utilizzare tutti i nomi di segnaposto che si desidera nei campi di testo del progetto.

Il valore Indice di partenza per il campo nella tabella Variabili di testo indica quale voce dell'elenco dei contenuti verrà utilizzata successivamente; zero significa la prima voce. L'indice viene automaticamente aumentato di uno alla fine di ogni singolo elemento processato.

Ma supponiamo, per motivi di efficienza, di voler masterizzare contemporaneamente due tag di prenotazione di posti, ciascuno con un nome diverso dallo stesso elenco. In questo caso, se il primo tag usa '{NAME#+0}' e il secondo '{NAME#+1}' (notare il segno più). '{NAME}' o '{NAME#+0}' utilizza la voce corrente (indicata dal valore dell'indice), '{NAME#+1}' utilizza la voce successiva a quella corrente, ecc.

Con questo sistema, è possibile utilizzare questi valori tutte le volte che si desidera nel proprio progetto.
Per far avanzare l'indice è necessario fare clic sui pulsanti Prev / Next della barra degli strumenti.

In alternativa all'inserimento manuale dei valori in Variabili di testo tramite il Gestione variabili di testo, è possibile utilizzare un file CSV standard separato da virgole. I nomi dei segnaposto sono definiti nella riga di intestazione standard del file CSV (la prima riga del file CSV) e i contenuti sono presi da tutte le righe successive. Il modo più semplice per creare un file CSV è utilizzare un foglio di calcolo, ad esempio Excel.

Le voci caricate da un file CSV vengono visualizzate come Tipo CSV ed è possibile impostare i valori dell'indice per tutte le voci CSV contemporaneamente.

Nota: se il CSV non ha una riga di intestazione, le colonne saranno denominate "colonna_1", "colonna_2" ecc.

L'elenco di parole contiene anche alcune voci speciali (che potrebbero essere particolarmente utili per i progetti di calibrazione):

	* 'version' - Versione di Meerk40t
	* 'date' - Data di inizio dell’incisione
	* 'time' - Ora di inizio dell’incisione
	* 'op_device' - Dispositivo su cui si sta effettuando l’incisione
	* 'op_speed' - Velocità dell'operazione corrente
	* 'op_power' - PPI dell'operazione corrente
	* 'op_dpi' - DPI dell'operazione corrente (raster)
	* 'op_passes' - Passaggi dell'operazione corrente

I segnaposto per "data" e "ora" possono anche contenere istruzioni di formattazione che consentono di formattarli secondo le convenzioni locali, ad esempio
	{date@%d.%m.%Y} - 31.12.2022
	{time@%H:%M} - 23:59

Per un insieme completo delle istruzioni di formattazione, vedere: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
french_wordlist_howto = """
Les listes de mots vous permettent de créer des éléments de texte dans votre conception contenant du texte d'espace réservé qui est remplacé au moment de la gravure à partir de cette liste de mots. Vous pouvez ainsi graver plusieurs éléments avec des textes différents sans avoir à modifier votre conception à chaque fois.

Un espace réservé consiste en un nom entre accolades, par exemple '{PRENOM}'. Vous utilisez ce nom dans l'éditeur de listes de mots pour l'associer à l'espace réservé et l'espace réservé sera remplacé par le texte que vous saisissez dans le contenu de la liste de mots associée.

Comme exemple d'utilisation de cette fonctionnalité, imaginez que vous voulez créer un ensemble d'étiquettes de réservation de places pour un dîner, chacune avec le nom d'une personne différente. Après avoir créé le chemin de découpe pour le contour de l'étiquette de nom, par exemple un rectangle, utilisez l'outil de dessin de texte pour créer un élément de texte contenant ce qui suit :
'Cette place est réservée pour {PRENOM}'

Ensuite, vous utilisez cet éditeur de listes de mots pour créer une ou plusieurs entrées comme suit :
    |-----------|------|-------|
    |    Nom    | Type | Index |
    |-----------|------|-------|
    | prenom    | Texte|   0   |
    |-----------|------|-------|
Puis cliquez sur la ligne 'prenom' et ajoutez plusieurs éléments au panneau Contenu, par exemple :
    Paul
    David
    Andy
Maintenant, lorsque vous exécutez la gravure, vous obtiendrez des étiquettes de place individuelles qui ont des noms différents, par exemple 'Cette place est réservée pour Andy'.

Vous pouvez utiliser autant de noms d'espaces réservés différents que vous le souhaitez dans les champs de texte de votre conception.

La valeur 'Index' dans la table de liste de mots indique quelle entrée de la liste de contenu sera utilisée ensuite, zéro signifiant la première entrée. L'index est automatiquement augmenté de un à la fin de chaque gravure.

Mais supposons que pour l'efficacité, vous voulez maintenant graver deux étiquettes de réservation de places en même temps, chacune ayant un nom différent de la même liste. Dans ce cas, si la première étiquette utilise '{NOM#+0}' et la seconde '{NOM#+1}' (notez le signe plus). '{NOM}' ou '{NOM#+0}' utilise l'entrée actuelle (pointée par la valeur Index), '{NOM#+1}' utilise l'entrée suivante après la courante, etc.

Avec l'usage ci-dessus, vous pouvez utiliser ces valeurs autant de fois que vous le souhaitez dans votre conception. Pour faire avancer l'index, vous devez cliquer sur les boutons Précédent / Suivant dans la barre d'outils.

Comme alternative à la saisie manuelle des valeurs de liste de mots en utilisant cet éditeur de listes de mots, vous pouvez utiliser un fichier CSV standard séparé par des virgules. Les noms d'espaces réservés sont définis dans la ligne d'en-tête CSV standard (la première ligne du fichier CSV), et le contenu est ensuite pris de toutes les lignes suivantes. Le moyen le plus simple de créer un fichier CSV est d'utiliser un tableur, par exemple Excel, cependant, par exemple pour les sites de commerce électronique, votre site web pourrait automatiquement créer le fichier CSV à partir des commandes passées en ligne par les clients.

Les entrées chargées à partir d'un fichier CSV sont affichées comme Type CSV, et vous pouvez définir les valeurs Index pour toutes les entrées CSV en même temps.

Note : Si votre CSV n'a pas de ligne d'en-tête, les colonnes seront nommées 'column_1', 'column_2', etc.

La liste de mots contient également quelques entrées spéciales (qui pourraient être particulièrement utiles pour les conceptions de calibrage) :
    * 'version'   - Version de Meerk40t
    * 'date'      - Date de début de la gravure
    * 'time'      - Heure de début de la gravure
    * 'op_device' - Appareil sur lequel vous gravez
    * 'op_speed'  - Vitesse de l'opération courante
    * 'op_power'  - PPI de l'opération courante
    * 'op_dpi'    - DPI de l'opération courante (trame)
    * 'op_passes' - Passes de l'opération courante

Les espaces réservés pour 'date' et 'time' peuvent également contenir des directives de formatage qui vous permettent de les formater selon vos conventions locales, par exemple :
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Pour un ensemble complet de directives de format, voir : https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
russian_wordlist_howto = """
Списки слов позволяют создавать текстовые элементы в дизайне, содержащие текст-заполнители, которые заменяются во время выжигания содержимым из данного списка слов. Таким образом можно выжигать несколько элементов с разным текстом, не изменяя каждый раз дизайн.

Заполнитель состоит из имени в фигурных скобках, например '{ИМЯФАМИЛИЯ}'. Вы используете это имя в редакторе списков слов, чтобы связать его с заполнителем, и заполнитель будет заменен текстом, который вы введете в связанное содержимое списка слов.

В качестве примера использования этой функциональности, представьте, что вы хотите создать набор карточек для резервирования мест на ужине, каждая с именем разного человека. Создав путь резки для контура именной карточки, например прямоугольник, используйте инструмент рисования текста для создания текстового элемента, содержащего следующее:
'Это место зарезервировано для {ИМЯФАМИЛИЯ}'

Затем используйте редактор списков слов для создания одной или нескольких записей следующим образом:
    |-----------|------|-------|
    |   Имя     | Тип  | Индекс|
    |-----------|------|-------|
    | имяфамилия| Текст|   0   |
    |-----------|------|-------|
Затем нажмите на строку 'имяфамилия' и добавьте несколько элементов в панель содержимого, например:
    Павел
    Давид
    Андрей
Теперь при выполнении выжигания вы получите индивидуальные карточки мест с разными именами, например 'Это место зарезервировано для Андрей'.

Вы можете использовать столько разных имен заполнителей, сколько захотите, в текстовых полях вашего дизайна.

Значение 'Индекс' в таблице списка слов указывает, какая запись в списке содержимого будет использована следующей, ноль означает первую запись. Индекс автоматически увеличивается на единицу в конце каждого выжигания.

Но предположим, что для эффективности вы теперь хотите выжечь две карточки резервирования мест одновременно, каждая с разным именем из того же списка. В этом случае, если первая карточка использует '{ИМЯ#+0}', а вторая '{ИМЯ#+1}' (обратите внимание на знак плюс). '{ИМЯ}' или '{ИМЯ#+0}' использует текущую запись (на которую указывает значение индекса), '{ИМЯ#+1}' использует следующую запись после текущей и т.д.

При таком использовании вы можете использовать эти значения столько раз, сколько захотите в вашем дизайне. Для продвижения индекса вам нужно нажать кнопки Пред/След в панели инструментов.

В качестве альтернативы ручному вводу значений списка слов с помощью этого редактора, вы можете использовать стандартный CSV-файл, разделенный запятыми. Имена заполнителей определяются в стандартной строке заголовка CSV (первая строка в CSV-файле), а содержимое затем берется из всех следующих строк. Самый простой способ создать CSV-файл - использовать электронную таблицу, например Excel, однако для сайтов электронной коммерции ваш веб-сайт может автоматически создать CSV-файл из заказов, размещенных онлайн клиентами.

Записи, загруженные из CSV-файла, показываются как тип CSV, и вы можете установить значения индекса для всех CSV-записей одновременно.

Примечание: Если ваш CSV не имеет строки заголовка, столбцы будут названы 'column_1', 'column_2' и т.д.

Список слов также содержит некоторые специальные записи (которые могут быть особенно полезны для калибровочных дизайнов):
    * 'version'   - Версия Meerk40t
    * 'date'      - Дата начала выжигания
    * 'time'      - Время начала выжигания
    * 'op_device' - Устройство, на котором вы выжигаете
    * 'op_speed'  - Скорость текущей операции
    * 'op_power'  - PPI текущей операции
    * 'op_dpi'    - DPI текущей (растровой) операции
    * 'op_passes' - Проходы операции текущей операции

Заполнители для 'date' и 'time' также могут содержать директивы форматирования, которые позволяют форматировать их согласно вашим местным соглашениям, например:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Для полного набора директив форматирования см.: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

english_material_howto = """
The Material Library Manager allows to create, maintain, use and manage operations that are customized to provide a desired effect with a given material (hence the name Material Library).
The parameters you want to use e.g. for cutting acrylic are very different from the ones you want to use to engrave a picture on slate.
You can share such a material setting with the MeerK40t community and you can benefit from the contributions of others by loading and using their settings.
"""
german_material_howto = """
Die Material-Bibliothek erlaubt es Arbeitsgangs-Einstellungen für spezifische Materialien anzulegen und zu verwalten.
Die Parameter, die man z.B. für das Schneiden von Acryl benötigt unterscheiden sich deutlich von denen, die man etwa zum Gravieren eine Fotos auf Schiefer braucht.
Diese Daten können im Übrigen mit der Meerk40t Commnity geteilt werden, un man im Gegenzug von den Beiträgen anderer profitieren.
"""
italian_material_howto = """
Il Gestore della libreria di materiali consente di creare, gestire, memorizzare e utilizzare i parametri di lavorazione per ottenere l'effetto desiderato con un determinato materiale.
I parametri da utilizzare, ad esempio, per tagliare l'acrilico sono molto diversi da quelli da utilizzare per incidere un'immagine sull'ardesia.
È possibile condividere tali impostazioni di lavorazione dei materiali con la comunità MeerK40t e beneficiare dei contributi degli altri caricando e utilizzando le loro impostazioni.
"""
french_material_howto = """
Le gestionnaire de bibliothèque de matériaux permet de créer, maintenir, utiliser et gérer des opérations qui sont personnalisées pour fournir un effet désiré avec un matériau donné (d'où le nom Bibliothèque de matériaux).
Les paramètres que vous voulez utiliser, par exemple pour découper de l'acrylique, sont très différents de ceux que vous voulez utiliser pour graver une image sur de l'ardoise.
Vous pouvez partager de tels paramètres de matériau avec la communauté MeerK40t et vous pouvez bénéficier des contributions des autres en chargeant et en utilisant leurs paramètres.
"""
russian_material_howto = """
Менеджер библиотеки материалов позволяет создавать, поддерживать, использовать и управлять операциями, которые настроены для обеспечения желаемого эффекта с определенным материалом (отсюда и название "Библиотека материалов").
Параметры, которые вы хотите использовать, например, для резки акрила, очень отличаются от тех, которые вы хотите использовать для гравировки изображения на сланце.
Вы можете поделиться такими настройками материала с сообществом MeerK40t и можете извлечь пользу из вкладов других, загружая и используя их настройки.
"""


def asset(context, asset):
    language = context.language
    lang = "english"
    # Language #00 : en - English
    if language == 0:  # ("en", "English", wx.LANGUAGE_ENGLISH)
        lang = "english"
    # Language #01 : it - italiano
    if language == 1:  # ("it", "italiano", wx.LANGUAGE_ITALIAN),
        lang = "italian"
    # Language #02 : fr - français
    if language == 2:  # ("fr", "français", wx.LANGUAGE_FRENCH),
        lang = "french"
    # Language #03 : de - Deutsch
    if language == 3:  # ("de", "Deutsch", wx.LANGUAGE_GERMAN),
        lang = "german"
    # Language #04 : es - español
    if language == 4:  # ("es", "español", wx.LANGUAGE_SPANISH),
        lang = "spanish"
    # Language #05 : zh - 中文
    if language == 5:  # ("zh", "中文", wx.LANGUAGE_CHINESE),
        lang = "chinese"
    # Language #06 : hu - Magyar
    if language == 6:  # ("hu", "Magyar", wx.LANGUAGE_HUNGARIAN),
        lang = "hungarian"
    # Language #07 : pt_PT - português
    if language == 7:  # ("pt_PT", "português", wx.LANGUAGE_PORTUGUESE),
        lang = "portuguese"
    # Language #08 : pt_BR - português brasileiro
    if (
        language == 8
    ):  # ("pt_BR", "português brasileiro", wx.LANGUAGE_PORTUGUESE_BRAZILIAN),
        lang = "portuguese_brazilian"
    # Language #09 : ja - 日本
    if language == 9:  # ("ja", "日本", wx.LANGUAGE_JAPANESE),
        lang = "japanese"
    # Language #10 : nl - Nederlands
    if language == 10:  # ("nl", "Nederlands", wx.LANGUAGE_DUTCH),
        lang = "dutch"
    # Language #11 : ru - русский
    if language == 11:  # ("ru", "русский", wx.LANGUAGE_RUSSIAN),
        lang = "russian"

    text = ""
    try:
        text = globals()[f"{lang}_{asset}"]
    except KeyError:
        try:
            text = globals()["english_" + asset]
        except KeyError:
            pass
    if text and text[0] == "\n":
        return text[1:]
    return text
