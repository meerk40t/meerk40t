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
spanish_wordlist_howto = """
Las Listas de Palabras le permiten crear elementos de texto en su diseño que contienen texto de marcador de posición que se reemplaza en el momento de la grabación desde esta Lista de Palabras. Así puede grabar varios elementos con diferentes textos sin tener que cambiar su diseño cada vez.

Un marcador de posición consiste en un nombre dentro de llaves, por ejemplo '{NOMBRE}'. Utilice el nombre en el Editor de Listas de Palabras para asociarlo con el marcador de posición y este será reemplazado por el texto que ingrese en el Contenido de la Lista de Palabras asociada.

Por ejemplo, imagine que quiere crear un conjunto de etiquetas de reserva de asientos para una cena, cada una con el nombre de una persona diferente. Habiendo creado el contorno de la etiqueta, por ejemplo un rectángulo, use la herramienta de texto para crear un elemento de texto que contenga lo siguiente:
'Este asiento está reservado para {NOMBRE}'

Luego use el editor de Listas de Palabras para crear una o más entradas como sigue:
    |-----------|------|-------|
    |   Nombre  | Tipo | Índice|
    |-----------|------|-------|
    | nombre    | Texto|   0   |
    |-----------|------|-------|
Después haga clic en la fila 'nombre' y agregue varios elementos al panel de Contenidos, por ejemplo:
    Pablo
    David
    Andy
Ahora, cuando ejecute la grabación, obtendrá etiquetas individuales con diferentes nombres, por ejemplo 'Este asiento está reservado para Andy'.

Puede usar tantos nombres de marcadores de posición como desee en los campos de texto de su diseño.

El valor 'Índice' en la tabla de la Lista de Palabras indica qué entrada de la lista de contenidos se usará a continuación, cero significa la primera entrada. El índice se incrementa automáticamente en uno al final de cada grabación.

Pero suponga que por eficiencia ahora quiere grabar dos etiquetas de reserva de asientos al mismo tiempo, cada una con un nombre diferente de la misma lista. En este caso, si la primera etiqueta usa '{NOMBRE#+0}' y la segunda '{NOMBRE#+1}' (note el signo de más). '{NOMBRE}' o '{NOMBRE#+0}' usa la entrada actual (apuntada por el valor de Índice), '{NOMBRE#+1}' usa la siguiente entrada después de la actual, etc.

Con el uso anterior, puede usar estos valores tantas veces como desee en su diseño. Para avanzar el índice debe hacer clic en los botones Anterior / Siguiente en la barra de herramientas.

Como alternativa a ingresar manualmente los valores de la lista de palabras usando este editor, puede usar un archivo CSV estándar separado por comas. Los nombres de los marcadores de posición se definen en la línea de encabezado estándar del CSV (la primera línea del archivo CSV), y el contenido se toma de todas las líneas siguientes. La forma más fácil de crear un archivo CSV es usando una hoja de cálculo, por ejemplo Excel, aunque para sitios de comercio electrónico su sitio web podría crear automáticamente el archivo CSV a partir de los pedidos realizados en línea por los clientes.

Las entradas cargadas desde un archivo CSV se muestran como Tipo CSV, y puede establecer los valores de Índice para todas las entradas CSV al mismo tiempo.

Nota: Si su CSV no tiene una línea de encabezado, las columnas se llamarán 'column_1', 'column_2', etc.

La lista de palabras también contiene algunas entradas especiales (que pueden ser especialmente útiles para diseños de calibración):
    * 'version'   - Versión de Meerk40t
    * 'date'      - Fecha de inicio de la grabación
    * 'time'      - Hora de inicio de la grabación
    * 'op_device' - Dispositivo en el que está grabando
    * 'op_speed'  - Velocidad de la operación actual
    * 'op_power'  - PPI de la operación actual
    * 'op_dpi'    - DPI de la operación actual (raster)
    * 'op_passes' - Pasadas de la operación actual

Los marcadores de posición para 'date' y 'time' también pueden contener directivas de formato que le permiten formatearlos según sus convenciones locales, por ejemplo:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Para un conjunto completo de directivas de formato, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
chinese_wordlist_howto = """
单词列表允许您在设计中创建包含占位符文本的文本元素，这些占位符文本将在烧录时由该单词列表中的内容替换。这样，您可以在不每次更改设计的情况下烧录多个带有不同文本的项目。

占位符由大括号中的名称组成，例如“{FIRSTNAME}”。您可以在单词列表编辑器中使用该名称将其与占位符关联，占位符将被您在相关单词列表内容中输入的文本替换。

例如，假设您想为晚宴创建一组座位预留标签，每个标签上都有不同的名字。创建好标签轮廓（例如一个矩形）后，使用文本绘图工具创建一个包含如下内容的文本元素：
“此座位保留给{FIRSTNAME}”

然后，您可以使用单词列表编辑器创建一个或多个如下条目：
    |-----------|------|-------|
    |   名称    | 类型 | 索引 |
    |-----------|------|-------|
    | firstname | 文本 |  0   |
    |-----------|------|-------|
然后点击“firstname”行，在内容面板中添加多个项目，例如：
    保罗
    大卫
    安迪
现在，当您执行烧录时，您将获得带有不同名字的单独座位标签，例如“此座位保留给安迪”。

您可以在设计的文本字段中使用任意数量的不同占位符名称。

单词列表表中的“索引”值指示下一个将使用内容列表中的哪个条目，零表示第一个条目。每次烧录结束时，索引会自动加一。

但假设为了提高效率，您现在想同时烧录两个座位预留标签，每个标签都来自同一个列表但名字不同。在这种情况下，如果第一个标签使用“{ISIM#+0}”，第二个使用“{ISIM#+1}”（加号请注意）。 “{ISIM}”或“{ISIM#+0}”使用当前条目（由索引值指向）， “{ISIM#+1}”使用当前条目之后的下一个条目，依此类推。

通过上述用法，您可以在设计中多次使用这些值。要推进索引，您需要点击工具栏上的上一个/下一个按钮。

除了使用此单词列表编辑器手动输入单词列表值外，您还可以使用标准逗号分隔的CSV文件。占位符名称在标准CSV头行（CSV文件的第一行）中定义，内容则取自所有后续行。创建CSV文件的最简单方法是使用电子表格（如Excel），当然，对于电商网站，您的网站也可以根据客户在线下单自动创建CSV文件。

从CSV文件加载的条目显示为类型CSV，您可以同时为所有CSV条目设置索引值。

注意：如果您的CSV没有头行，列将被命名为“column_1”、“column_2”等。

单词列表还包含一些特殊条目（对于校准设计可能特别有用）：
    * 'version'   - Meerk40t版本
    * 'date'      - 烧录开始日期
    * 'time'      - 烧录开始时间
    * 'op_device' - 您正在烧录的设备
    * 'op_speed'  - 当前操作的速度
    * 'op_power'  - 当前操作的PPI
    * 'op_dpi'    - 当前（光栅）操作的DPI
    * 'op_passes' - 当前操作的遍数

“date”和“time”的占位符还可以包含格式指令，允许您根据本地习惯对其进行格式化，例如：
    {date@%Y.%m.%d} - 2022.12.31
    {time@%H:%M} - 23:59

完整的格式指令请参见：https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
hungarian_wordlist_howto = """
A Szólisták lehetővé teszik, hogy a tervezésben olyan szövegelemeket hozzon létre, amelyek helyőrző szöveget tartalmaznak, és ezeket a szólistából származó tartalommal cseréli ki az égetés során. Így több elemet is égethet különböző szövegekkel anélkül, hogy minden alkalommal módosítania kellene a tervet.

A helyőrző egy név, amely kapcsos zárójelek között van, például '{KERESZTNÉV}'. A Szólista szerkesztőben ezt a nevet használja a helyőrzőhöz való társításhoz, és a helyőrzőt az Ön által a kapcsolódó Szólista tartalmába beírt szöveg váltja fel.

Például, ha vacsorához szeretne ülésfoglaló címkéket készíteni, mindegyiken más-más névvel, akkor hozzon létre egy névcímke körvonalat (például egy téglalapot), majd a Szöveg eszközzel hozzon létre egy szövegelemet, amely a következőt tartalmazza:
'Ez a hely {KERESZTNÉV} számára van fenntartva'

Ezután a Szólista szerkesztővel hozzon létre egy vagy több bejegyzést az alábbiak szerint:
    |-----------|------|-------|
    |   Név     | Típus| Index |
    |-----------|------|-------|
    | keresztnev| Szöveg|  0   |
    |-----------|------|-------|
Ezután kattintson a 'keresztnev' sorra, és adjon hozzá több elemet a Tartalom panelhez, például:
    Pál
    Dávid
    András
Most, amikor végrehajtja az égetést, egyedi helycímkéket kap, amelyek különböző neveket tartalmaznak, például 'Ez a hely András számára van fenntartva'.

A tervezés szövegmezőiben annyi különböző helyőrző nevet használhat, amennyit csak szeretne.

A Szólista táblázat 'Index' értéke azt jelzi, hogy a Tartalom listából melyik bejegyzést használja legközelebb, a nulla az első bejegyzést jelenti. Az index minden égetés végén automatikusan eggyel növekszik.

Ha azonban hatékonyság szempontjából most két ülésfoglaló címkét szeretne egyszerre égetni, mindegyik más-más névvel ugyanabból a listából, akkor az első címke '{NÉV#+0}', a második pedig '{NÉV#+1}' (figyelje a plusz jelet). A '{NÉV}' vagy '{NÉV#+0}' a jelenlegi bejegyzést használja (amelyre az Index érték mutat), a '{NÉV#+1}' a jelenlegi utáni következő bejegyzést stb.

A fenti használattal ezeket az értékeket annyiszor használhatja a tervezésben, ahányszor csak szeretné. Az index előrehaladásához kattintson az Előző/Következő gombokra az eszköztáron.

A szólista értékeit nemcsak manuálisan viheti be a Szólista szerkesztővel, hanem használhat szabványos, vesszővel elválasztott CSV-fájlt is. A helyőrző neveket a szabványos CSV-fejléc sorban (a CSV-fájl első sora) határozza meg, a tartalmat pedig az összes következő sorból veszi. A CSV-fájl létrehozásának legegyszerűbb módja egy táblázatkezelő, például az Excel használata, de például webáruházak esetén a weboldal automatikusan létrehozhatja a CSV-fájlokat az online leadott rendelésekből.

A CSV-fájlban betöltött bejegyzések típusa CSV-ként jelenik meg, és az összes CSV-bejegyzés indexértékét egyszerre beállíthatja.

Megjegyzés: Ha a CSV-fájlban nincs fejlécsor, az oszlopokat 'column_1', 'column_2' stb. néven nevezi el.

A szólista néhány speciális bejegyzést is tartalmaz (amelyek különösen hasznosak lehetnek kalibrációs tervekhez):
    * 'version'   - Meerk40t verzió
    * 'date'      - Az égetés kezdési dátuma
    * 'time'      - Az égetés kezdési ideje
    * 'op_device' - Az eszköz, amelyen éget
    * 'op_speed'  - Az aktuális művelet sebessége
    * 'op_power'  - Az aktuális művelet PPI-je
    * 'op_dpi'    - Az aktuális (raszteres) művelet DPI-je
    * 'op_passes' - Az aktuális művelet átfutásai

A 'date' és 'time' helyőrzők formázási utasításokat is tartalmazhatnak, amelyek lehetővé teszik, hogy azokat a helyi szokásoknak megfelelően formázza, például:
    {date@%Y.%m.%d} - 2022.12.31
    {time@%H:%M} - 23:59

A formátumutasítások teljes készletéhez lásd: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
portuguese_wordlist_howto = """
As Listas de Palavras permitem criar elementos de texto no seu design que contêm texto de espaço reservado, substituído no momento da gravação pelo conteúdo desta Lista de Palavras. Assim, pode gravar vários itens com textos diferentes sem ter de alterar o design de cada vez.

Um espaço reservado consiste num nome entre chavetas, por exemplo '{NOME}'. Utilize o nome no Editor de Listas de Palavras para o associar ao espaço reservado e este será substituído pelo texto que inserir no Conteúdo da Lista de Palavras associada.

Por exemplo, imagine que quer criar um conjunto de etiquetas de reserva de lugares para um jantar, cada uma com o nome de uma pessoa diferente. Depois de criar o contorno da etiqueta, por exemplo um retângulo, utilize a ferramenta de texto para criar um elemento de texto com o seguinte conteúdo:
'Este lugar está reservado para {NOME}'

Depois, utilize o editor de Listas de Palavras para criar uma ou mais entradas como segue:
    |-----------|------|-------|
    |   Nome    | Tipo | Índice|
    |-----------|------|-------|
    | nome      | Texto|   0   |
    |-----------|------|-------|
Depois clique na linha 'nome' e adicione vários itens ao painel de Conteúdo, por exemplo:
    Paulo
    David
    Andy
Agora, ao executar a gravação, obterá etiquetas individuais com nomes diferentes, por exemplo 'Este lugar está reservado para Andy'.

Pode usar tantos nomes de espaços reservados quantos quiser nos campos de texto do seu design.

O valor 'Índice' na tabela da Lista de Palavras indica qual entrada da lista de conteúdos será usada a seguir, sendo zero a primeira entrada. O índice é automaticamente incrementado em um no final de cada gravação.

Mas suponha que, por eficiência, agora quer gravar duas etiquetas de reserva de lugares ao mesmo tempo, cada uma com um nome diferente da mesma lista. Neste caso, se a primeira etiqueta usar '{NOME#+0}' e a segunda '{NOME#+1}' (note o sinal de mais). '{NOME}' ou '{NOME#+0}' usa a entrada atual (apontada pelo valor do Índice), '{NOME#+1}' usa a próxima entrada após a atual, etc.

Com o uso acima, pode usar estes valores quantas vezes quiser no seu design. Para avançar o índice, deve clicar nos botões Anterior / Seguinte na barra de ferramentas.

Como alternativa à introdução manual dos valores da lista de palavras usando este editor, pode usar um ficheiro CSV padrão separado por vírgulas. Os nomes dos espaços reservados são definidos na linha de cabeçalho padrão do CSV (a primeira linha do ficheiro CSV), e o conteúdo é retirado de todas as linhas seguintes. A forma mais fácil de criar um ficheiro CSV é usando uma folha de cálculo, por exemplo o Excel, mas para sites de comércio eletrónico o seu site pode criar automaticamente o ficheiro CSV a partir das encomendas feitas online pelos clientes.

As entradas carregadas de um ficheiro CSV são apresentadas como Tipo CSV, e pode definir os valores de Índice para todas as entradas CSV ao mesmo tempo.

Nota: Se o seu CSV não tiver uma linha de cabeçalho, as colunas serão nomeadas 'column_1', 'column_2', etc.

A lista de palavras também contém algumas entradas especiais (que podem ser especialmente úteis para designs de calibração):
    * 'version'   - Versão do Meerk40t
    * 'date'      - Data de início da gravação
    * 'time'      - Hora de início da gravação
    * 'op_device' - Dispositivo em que está a gravar
    * 'op_speed'  - Velocidade da operação atual
    * 'op_power'  - PPI da operação atual
    * 'op_dpi'    - DPI da operação atual (raster)
    * 'op_passes' - Passagens da operação atual

Os espaços reservados para 'date' e 'time' também podem conter diretivas de formatação que permitem formatá-los de acordo com as suas convenções locais, por exemplo:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Para um conjunto completo de diretivas de formato, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
portuguese_brazilian_wordlist_howto = """
As Listas de Palavras permitem criar elementos de texto no seu design que contêm texto de espaço reservado, substituído no momento da gravação pelo conteúdo desta Lista de Palavras. Assim, pode gravar vários itens com textos diferentes sem ter de alterar o design de cada vez.

Um espaço reservado consiste num nome entre chaves, por exemplo '{NOME}'. Utilize o nome no Editor de Listas de Palavras para o associar ao espaço reservado e este será substituído pelo texto que inserir no Conteúdo da Lista de Palavras associada.

Por exemplo, imagine que quer criar um conjunto de etiquetas de reserva de lugares para um jantar, cada uma com o nome de uma pessoa diferente. Depois de criar o contorno da etiqueta, por exemplo um retângulo, utilize a ferramenta de texto para criar um elemento de texto com o seguinte conteúdo:
'Este lugar está reservado para {NOME}'

Depois, utilize o editor de Listas de Palavras para criar uma ou mais entradas como segue:
    |-----------|------|-------|
    |   Nome    | Tipo | Índice|
    |-----------|------|-------|
    | nome      | Texto|   0   |
    |-----------|------|-------|
Depois clique na linha 'nome' e adicione vários itens ao painel de Conteúdo, por exemplo:
    Paulo
    David
    Andy
Agora, ao executar a gravação, obterá etiquetas individuais com nomes diferentes, por exemplo 'Este lugar está reservado para Andy'.

Pode usar tantos nomes de espaços reservados quantos quiser nos campos de texto do seu design.

O valor 'Índice' na tabela da Lista de Palavras indica qual entrada da lista de conteúdos será usada a seguir, sendo zero a primeira entrada. O índice é automaticamente incrementado em um no final de cada gravação.

Mas suponha que, por eficiência, agora quer gravar duas etiquetas de reserva de lugares ao mesmo tempo, cada uma com um nome diferente da mesma lista. Neste caso, se a primeira etiqueta usar '{NOME#+0}' e a segunda '{NOME#+1}' (note o sinal de mais). '{NOME}' ou '{NOME#+0}' usa a entrada atual (apontada pelo valor do Índice), '{NOME#+1}' usa a próxima entrada após a atual, etc.

Com o uso acima, pode usar estes valores quantas vezes quiser no seu design. Para avançar o índice, deve clicar nos botões Anterior / Seguinte na barra de ferramentas.

Como alternativa à introdução manual dos valores da lista de palavras usando este editor, pode usar um ficheiro CSV padrão separado por vírgulas. Os nomes dos espaços reservados são definidos na linha de cabeçalho padrão do CSV (a primeira linha do ficheiro CSV), e o conteúdo é retirado de todas as linhas seguintes. A forma mais fácil de criar um ficheiro CSV é usando uma folha de cálculo, por exemplo o Excel, mas para sites de comércio eletrónico o seu site pode criar automaticamente o ficheiro CSV a partir das encomendas feitas online pelos clientes.

As entradas carregadas de um ficheiro CSV são apresentadas como Tipo CSV, e pode definir os valores de Índice para todas as entradas CSV ao mesmo tempo.

Nota: Se o seu CSV não tiver uma linha de cabeçalho, as colunas serão nomeadas 'column_1', 'column_2', etc.

A lista de palavras também contém algumas entradas especiais (que podem ser especialmente úteis para designs de calibração):
    * 'version'   - Versão do Meerk40t
    * 'date'      - Data de início da gravação
    * 'time'      - Hora de início da gravação
    * 'op_device' - Dispositivo em que está a gravar
    * 'op_speed'  - Velocidade da operação atual
    * 'op_power'  - PPI da operação atual
    * 'op_dpi'    - DPI da operação atual (raster)
    * 'op_passes' - Passagens da operação atual

Os espaços reservados para 'date' e 'time' também podem conter diretivas de formatação que permitem formatá-los de acordo com as suas convenções locais, por exemplo:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Para um conjunto completo de diretivas de formato, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""
japanese_wordlist_howto = """
ワードリストを使用すると、デザイン内のテキスト要素にプレースホルダーテキストを含めることができ、焼成時にこのワードリストから内容に置き換えられます。これにより、毎回デザインを変更することなく、異なるテキストを持つ複数のアイテムを焼成できます。

プレースホルダーは中括弧内の名前で構成されます。例: '{FIRSTNAME}'。ワードリストエディタでこの名前を使用してプレースホルダーと関連付けると、関連付けられたワードリストの内容に入力したテキストでプレースホルダーが置き換えられます。

この機能の使用例として、ディナーパーティーの席予約タグを作成したいとします。各タグには異なる人の名前が入っています。名札の輪郭（例：長方形）を作成した後、テキスト描画ツールを使用して次の内容を含むテキスト要素を作成します：
「この席は{FIRSTNAME}のために予約されています」

次に、このワードリストエディタを使用して、次のようなエントリを1つ以上作成します：
    |-----------|------|-------|
    |   名前    | 種類 | インデックス |
    |-----------|------|-------|
    | firstname | テキスト | 0   |
    |-----------|------|-------|
次に「firstname」行をクリックし、内容ペインにいくつかの項目を追加します。例：
    ポール
    デイビッド
    アンディ
これで焼成を実行すると、「この席はアンディのために予約されています」のように、異なる名前が入った個別の席札が得られます。

デザインのテキストフィールドには、好きなだけ多くの異なるプレースホルダー名を使用できます。

ワードリストテーブルの「インデックス」値は、次に使用される内容リストのエントリを示します。ゼロは最初のエントリを意味します。インデックスは各焼成の最後に自動的に1つ増加します。

効率のために、同じリストから異なる名前を持つ2つの席予約タグを同時に焼成したい場合、最初のタグは「{ISIM#+0}」、2番目は「{ISIM#+1}」（プラス記号に注意）を使用します。「{ISIM}」または「{ISIM#+0}」使用中のエントリ（インデックス値が指すもの）を、「{ISIM#+1}」は現在の次のエントリを使用します。

上記の使い方で、これらの値はデザイン内で何度でも使用できます。インデックスを進めるには、ツールバーの前/次ボタンをクリックします。

このワードリストエディタを使用して手動で値を入力する代わりに、標準のカンマ区切りCSVファイルを使用することもできます。プレースホルダー名は標準のCSVヘッダー行（CSVファイルの最初の行）で定義され、内容はすべての後続行から取得されます。CSVファイルを作成する最も簡単な方法は、Excelなどのスプレッドシートを使用することです。ECサイトの場合、ウェブサイトが顧客の注文から自動的にCSVファイルを作成することもできます。

CSVファイルから読み込まれたエントリはタイプCSVとして表示され、すべてのCSVエントリのインデックス値を同時に設定できます。

注意：CSVにヘッダー行がない場合、列は「column_1」、「column_2」などと名付けられます。

ワードリストには、いくつかの特別なエントリも含まれています（キャリブレーションデザインに特に便利です）：
    * 'version'   - Meerk40tバージョン
    * 'date'      - 烧录开始日期
    * 'time'      - 烧录开始时刻
    * 'op_device' - 使用しているデバイス
    * 'op_speed'  - 現在の操作の速度
    * 'op_power'  - 現在の操作のPPI
    * 'op_dpi'    - 現在（ラスター）操作のDPI
    * 'op_passes' - 現在の操作のパス数

「date」と「time」のプレースホルダーには、ローカルの規則に従ってフォーマットできる書式指定子を含めることもできます。例：
    {date@%Y.%m.%d} - 2022.12.31
    {time@%H:%M} - 23:59

書式指定子の完全なセットについては、https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior を参照してください。
"""
dutch_wordlist_howto = """
Met Woordenlijsten kunt u textelementen in uw ontwerp maken die tijdelijke tekst bevatten die bij het branden wordt vervangen door deze Woordenlijst. U kunt dan meerdere items met verschillende tekst branden zonder uw ontwerp telkens te hoeven wijzigen.

Een tijdelijke aanduiding bestaat uit een naam tussen accolades, bijvoorbeeld '{VOORNAAM}'. U gebruikt de naam in de Woordenlijst-editor om deze te koppelen aan de tijdelijke aanduiding en de tijdelijke aanduiding wordt vervangen door de tekst die u invoert in de bijbehorende Woordenlijst-inhoud.

Als voorbeeld van hoe deze functionaliteit wordt gebruikt, stel dat u een set zitplaatsreserveringslabels voor een diner wilt maken, elk met een andere naam. Nadat u het snijpad voor de naamlabelomtrek hebt gemaakt, bijvoorbeeld een rechthoek, gebruikt u het tekstgereedschap om een textelement te maken met de volgende inhoud:
'Deze stoel is gereserveerd voor {VOORNAAM}'

Gebruik vervolgens deze Woordenlijst-editor om een of meer items als volgt te maken:
    |-----------|------|-------|
    |   Naam    | Type | Index |
    |-----------|------|-------|
    | voornaam  | Tekst|   0   |
    |-----------|------|-------|
Klik vervolgens op de rij 'voornaam' en voeg meerdere items toe aan het inhoudspaneel, bijvoorbeeld:
    Paul
    David
    Andy
Wanneer u nu het branden uitvoert, krijgt u individuele plaatslabels met verschillende namen, bijvoorbeeld 'Deze stoel is gereserveerd voor Andy'.

U kunt zoveel verschillende tijdelijke aanduidingsnamen gebruiken als u wilt in tekstvelden in uw ontwerp.

De 'Index'-waarde in de Woordenlijsttabel geeft aan welk item in de inhoudslijst de volgende keer wordt gebruikt, waarbij nul het eerste item betekent. De index wordt automatisch met één verhoogd aan het einde van elke brand.

Stel dat u nu om efficiëntie twee zitplaatsreserveringslabels tegelijk wilt branden, elk met een andere naam uit dezelfde lijst. In dit geval, als het eerste label '{NAAM#+0}' gebruikt en het tweede '{NAAM#+1}' (let op het plusteken). '{NAAM}' of '{NAAM#+0}' gebruikt het huidige item (aangegeven door de Index-waarde), '{NAAM#+1}' gebruikt het volgende item na het huidige, enzovoort.

Met het bovenstaande gebruik kunt u deze waarden zo vaak gebruiken als u wilt in uw ontwerp. Om de index te verhogen, moet u op de Vorige / Volgende knoppen in de werkbalk klikken.

Als alternatief voor het handmatig invoeren van de waarden van de woordenlijst met deze editor, kunt u een standaard door komma's gescheiden CSV-bestand gebruiken. De tijdelijke aanduidingsnamen worden gedefinieerd in de standaard CSV-kopregel (de eerste regel in het CSV-bestand), en de inhoud wordt vervolgens uit alle volgende regels gehaald. De eenvoudigste manier om een CSV-bestand te maken is met een spreadsheet, bijvoorbeeld Excel, maar voor webwinkels kan uw website het CSV-bestand automatisch aanmaken op basis van online geplaatste bestellingen van klanten.

Items die uit een CSV-bestand zijn geladen, worden weergegeven als Type CSV, en u kunt de Index-waarden voor alle CSV-items tegelijk instellen.

Opmerking: als uw CSV geen kopregel heeft, worden de kolommen 'column_1', 'column_2', enz. genoemd.

De woordenlijst bevat ook enkele speciale items (die vooral handig kunnen zijn voor kalibratieontwerpen):
    * 'version'   - Meerk40t-versie
    * 'date'      - Datum waarop het branden is gestart
    * 'time'      - Tijd waarop het branden is gestart
    * 'op_device' - Apparaat waarop u brandt
    * 'op_speed'  - Snelheid van de huidige bewerking
    * 'op_power'  - PPI van de huidige bewerking
    * 'op_dpi'    - DPI van de huidige (raster) bewerking
    * 'op_passes' - Aantal passes van de huidige bewerking

De tijdelijke aanduidingen voor 'date' en 'time' kunnen ook opmaakopdrachten bevatten waarmee u ze kunt opmaken volgens uw lokale conventies, bijvoorbeeld:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Voor een volledige set opmaakopdrachten, zie: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

turkish_wordlist_howto = """
Kelime Listeleri, tasarımınızda yer tutucu metin içeren metin öğeleri oluşturmanıza olanak tanır. Bu yer tutucu metin, yakma sırasında bu Kelime Listesinden alınan içerikle değiştirilir. Böylece, tasarımınızı her seferinde değiştirmek zorunda kalmadan farklı metinlere sahip birden fazla öğe yakabilirsiniz.

Bir yer tutucu, süslü parantezler içinde bir isimdan oluşur, örneğin '{ISIM}'. Bu ismi Kelime Listesi Düzenleyicisinde kullanarak yer tutucu ile ilişkilendirirsiniz ve yer tutucu, ilgili Kelime Listesi İçeriğine girdiğiniz metinle değiştirilir.

Bu işlevin nasıl kullanılacağına bir örnek olarak, her birinde farklı bir kişinin adı olan bir dizi akşam yemeği rezervasyon etiketi oluşturmak istediğinizi hayal edin. Ad etiketinin dış hatlarını (örneğin bir dikdörtgen) oluşturduktan sonra, Metin çizim aracını kullanarak aşağıdaki metni içeren bir Metin öğesi oluşturun:
'Bu koltuk {ISIM} için ayrılmıştır'

Daha sonra bu Kelime Listesi düzenleyicisini kullanarak aşağıdaki gibi bir veya daha fazla giriş oluşturun:
    |-----------|------|-------|
    |   İsim    | Tip  | İndeks|
    |-----------|------|-------|
    | isim      | Metin|   0   |
    |-----------|------|-------|
Ardından 'isim' satırına tıklayın ve İçerik paneline birkaç öğe ekleyin, örneğin:
    Ahmet
    Mehmet
    Ayşe
Artık yakma işlemini gerçekleştirdiğinizde, üzerinde farklı isimler olan bireysel yer etiketi alırsınız, örneğin 'Bu koltuk Ayşe için ayrılmıştır'.

Tasarımınızda metin alanlarında istediğiniz kadar farklı yer tutucu ismi kullanabilirsiniz.

Kelime Listesi tablosundaki 'İndeks' değeri, içerik listesinden bir sonraki hangi girişin kullanılacağını gösterir, sıfır ilk girişi ifade eder. İndeks, her yakma işleminin sonunda otomatik olarak bir artırılır.

Verimlilik açısından artık aynı listeden farklı isimlerle iki koltuk rezervasyon etiketini aynı anda yakmak istediğinizi varsayalım. Bu durumda, ilk etiket '{ISIM#+0}', ikinci ise '{ISIM#+1}' kullanır (artı işaretine dikkat edin). '{ISIM}' veya '{ISIM#+0}' mevcut girişi (İndeks değeriyle gösterilen), '{ISIM#+1}' ise mevcut girişten sonraki bir sonraki girişi kullanır.

Yukarıdaki kullanım ile bu değerleri tasarımınızda istediğiniz kadar kullanabilirsiniz. İndeksi ilerletmek için araç çubuğundaki Önceki / Sonraki düğmelerine tıklamanız gerekir.

Kelime Listesi değerlerini bu Kelime Listesi Düzenleyicisi ile manuel olarak girmek yerine, standart virgülle ayrılmış bir CSV dosyası da kullanabilirsiniz. Yer tutucu isimleri standart CSV başlık satırında (CSV dosyasının ilk satırı) tanımlanır, içerik tüm sonraki satırlardan alınır. Bir CSV dosyası oluşturmanın en kolay yolu bir elektronik tablo (örneğin Excel) kullanmaktır, ancak e-ticaret siteleri için web siteniz müşteriler tarafından çevrimiçi verilen siparişlerden CSV dosyasını otomatik olarak oluşturabilir.

CSV dosyasından yüklenen girişler Tip CSV olarak gösterilir ve tüm CSV girişleri için İndeks değerlerini aynı anda ayarlayabilirsiniz.

Not: CSV'nizin başlık satırı yoksa, sütunlar 'column_1', 'column_2' vb. olarak adlandırılır.

Kelime Listesi ayrıca bazı özel girişler içerir (özellikle kalibrasyon tasarımları için faydalı olabilir):
    * 'version'   - Meerk40t sürümü
    * 'date'      - Yakma işlemi başlangıç tarihi
    * 'time'      - Yakma işlemi başlangıç saati
    * 'op_device' - Yakma yaptığınız cihaz
    * 'op_speed'  - Mevcut işlemin hızı
    * 'op_power'  - Mevcut işlemin PPI değeri
    * 'op_dpi'    - Mevcut (raster) işlemin DPI değeri
    * 'op_passes' - Mevcut işlemin geçiş sayısı

'date' ve 'time' için yer tutucular ayrıca yerel alışkanlıklarınıza göre biçimlendirmenize olanak tanıyan biçimlendirme yönergeleri içerebilir, örneğin:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Tam biçimlendirme yönergeleri için bkz.: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
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
spanish_material_howto = """
El Gestor de la Biblioteca de Materiales permite crear, mantener, usar y gestionar operaciones que están personalizadas para proporcionar un efecto deseado con un material dado (de ahí el nombre Biblioteca de Materiales).
Los parámetros que desea utilizar, por ejemplo, para cortar acrílico son muy diferentes de los que desea utilizar para grabar una imagen en pizarra.
Puede compartir dicha configuración de material con la comunidad de MeerK40t y beneficiarse de las contribuciones de otros cargando y utilizando sus configuraciones.
"""
chinese_material_howto = """
材料库管理器允许您创建、维护、使用和管理针对特定材料定制的操作（因此称为材料库）。
例如，用于切割亚克力的参数与用于在石板上雕刻图像的参数非常不同。
您可以与MeerK40t社区分享此类材料设置，也可以通过加载和使用他人的设置来受益于他人的贡献。
"""
hungarian_material_howto = """
Az Anyagkönyvtár kezelő lehetővé teszi, hogy létrehozzon, karbantartson, használjon és kezeljen olyan műveleteket, amelyek egy adott anyaghoz igazított hatást biztosítanak (innen az Anyagkönyvtár elnevezés).
Az akril vágásához használt paraméterek például nagyon eltérnek azoktól, amelyeket pala gravírozásához használna.
Az ilyen anyagbeállításokat megoszthatja a MeerK40t közösséggel, és mások hozzájárulásaiból is profitálhat, ha betölti és használja az ő beállításaikat.
"""
portuguese_material_howto = """
O Gerenciador de Biblioteca de Materiais permite criar, manter, usar e gerenciar operações que são personalizadas para fornecer um efeito desejado com um determinado material (daí o nome Biblioteca de Materiais).
Os parâmetros que você deseja usar, por exemplo, para cortar acrílico, são muito diferentes dos que você deseja usar para gravar uma imagem em ardósia.
Você pode compartilhar essa configuração de material com a comunidade MeerK40t e pode se beneficiar das contribuições de outros carregando e usando suas configurações.
"""
portuguese_brazilian_material_howto = """
O Gerenciador de Biblioteca de Materiais permite criar, manter, usar e gerenciar operações que são personalizadas para fornecer um efeito desejado com um determinado material (daí o nome Biblioteca de Materiais).
Os parâmetros que você deseja usar, por exemplo, para cortar acrílico, são muito diferentes dos que você deseja usar para gravar uma imagem em ardósia.
Você pode compartilhar essa configuração de material com a comunidade MeerK40t e pode se beneficiar das contribuições de outros carregando e usando suas configurações.
"""
japanese_material_howto = """
マテリアルライブラリマネージャーは、特定の材料で望ましい効果を得るためにカスタマイズされた操作を作成、維持、使用、管理することができます（そのため「マテリアルライブラリ」と呼ばれます）。
例えば、アクリルをカットするために使用するパラメータは、スレートに画像を彫刻するために使用するパラメータとは大きく異なります。
このようなマテリアル設定をMeerK40tコミュニティと共有したり、他の人の設定を読み込んで利用することで、その貢献から恩恵を受けることができます。
"""
dutch_material_howto = """
De Materialenbibliotheekbeheerder stelt u in staat om bewerkingen te maken, te onderhouden, te gebruiken en te beheren die zijn aangepast om een gewenst effect te bereiken met een bepaald materiaal (vandaar de naam Materialenbibliotheek).
De parameters die u bijvoorbeeld wilt gebruiken voor het snijden van acryl zijn heel anders dan die voor het graveren van een afbeelding op leisteen.
U kunt dergelijke materiaalsinstellingen delen met de MeerK40t-gemeenschap en profiteren van de bijdragen van anderen door hun instellingen te laden en te gebruiken.
"""

turkish_material_howto = """
Malzeme Kütüphanesi Yöneticisi, belirli bir malzeme ile istenen etkiyi sağlamak için özelleştirilmiş işlemler oluşturmanıza, sürdürmenize, kullanmanıza ve yönetmenize olanak tanır (bu nedenle adı Malzeme Kütüphanesi'dir).
Örneğin, akrilik kesmek için kullanmak istediğiniz parametreler, arduvaz üzerine bir resim kazımak için kullanmak istediklerinizden çok farklıdır.
Bu tür bir malzeme ayarını MeerK40t topluluğu ile paylaşabilir ve başkalarının katkılarından yararlanmak için onların ayarlarını yükleyip kullanabilirsiniz.
"""

polish_wordlist_howto = """
Listy słów pozwalają na tworzenie elementów tekstowych w projekcie, które zawierają tekst zastępczy, zastępowany podczas wypalania zawartością z tej Listy słów. Możesz wtedy wypalić kilka elementów z różnym tekstem bez konieczności zmiany projektu za każdym razem.

Zastępca składa się z nazwy w nawiasach klamrowych, np. '{IMIE}'. Używasz nazwy w Edytorze listy słów, aby powiązać ją z zastępcą, a zastępca zostanie zastąpiony tekstem, który wprowadzisz do powiązanej Zawartości listy słów.

Jako przykład użycia tej funkcjonalności, wyobraź sobie, że chcesz stworzyć zestaw etykiet rezerwacji miejsc na kolację, każda z innym imieniem osoby. Po utworzeniu ścieżki cięcia dla obrysu etykiety z nazwiskiem, np. prostokąta, użyj narzędzia rysowania tekstu, aby utworzyć element tekstowy zawierający następujące:
'To miejsce jest zarezerwowane dla {IMIE}'

Następnie używasz tego edytora listy słów, aby utworzyć jedną lub więcej wpisów w następujący sposób:
	|-----------|------|-------|
	|    Nazwa  | Typ  | Indeks|
	|-----------|------|-------|
	| imie      | Tekst|   0   |
	|-----------|------|-------|
Następnie kliknij na wierszu 'imie' i dodaj kilka elementów do panelu Zawartości, np.:
	Paweł
	David
	Andy
Teraz, gdy wykonasz wypalanie, otrzymasz indywidualne etykiety miejsc z różnymi nazwami, np. 'To miejsce jest zarezerwowane dla Andy'.

Możesz używać tyle różnych nazw zastępczych, ile chcesz w polach tekstowych w projekcie.

Wartość 'Indeks' w tabeli Listy słów wskazuje, który wpis na liście Zawartości zostanie użyty następny, zero oznacza pierwszy wpis. Indeks jest automatycznie zwiększany o jeden na końcu każdego wypalania.

Ale załóżmy, że dla efektywności chcesz teraz wypalić dwie etykiety rezerwacji miejsc jednocześnie, każda z innym imieniem z tej samej listy. W tym przypadku, jeśli pierwsza etykieta używa '{NAZWA#+0}', a druga '{NAZWA#+1}' (zwróć uwagę na znak plus). '{NAZWA}' lub '{NAZWA#+0}' używa bieżącego wpisu (wskazywanego przez wartość Indeksu), '{NAZWA#+1}' używa następnego wpisu po bieżącym itp.

Przy powyższym użyciu możesz używać tych wartości tyle razy, ile chcesz w projekcie. Aby przesunąć indeks, musisz kliknąć przyciski Poprzedni / Następny na pasku narzędzi.

Jako alternatywę dla ręcznego wprowadzania wartości listy słów za pomocą tego Edytora listy słów, możesz użyć standardowego pliku CSV rozdzielanego przecinkami. Nazwy zastępcze są zdefiniowane w standardowej linii nagłówka CSV (pierwsza linia w pliku CSV), a zawartość jest następnie pobierana ze wszystkich następnych linii. Najłatwiejszym sposobem utworzenia pliku CSV jest użycie arkusza kalkulacyjnego, np. Excel, jednak np. dla stron e-commerce Twoja strona może automatycznie utworzyć plik CSV z zamówień złożonych online przez klientów.

Wpisy załadowane z pliku CSV są wyświetlane jako Typ CSV, i możesz ustawić wartości Indeksu dla wszystkich wpisów CSV jednocześnie.

Uwaga: Jeśli Twój CSV nie ma linii nagłówka, kolumny będą nazwane 'column_1', 'column_2' itp.

Lista słów zawiera również niektóre specjalne wpisy (które mogą być szczególnie przydatne dla projektów kalibracyjnych):
	* 'version'   - Wersja Meerk40t
	* 'date'      - Data rozpoczęcia wypalania
	* 'time'      - Czas rozpoczęcia wypalania
	* 'op_device' - Urządzenie, na którym wypalasz
	* 'op_speed'  - Prędkość bieżącej operacji
	* 'op_power'  - PPI bieżącej operacji
	* 'op_dpi'    - DPI bieżącej (rastrowej) operacji
	* 'op_passes' - Przejścia operacji bieżącej operacji

Zastępcy dla 'date' i 'time' mogą również zawierać dyrektywy formatowania, które pozwalają formatować je zgodnie z lokalnymi konwencjami, np.
	{date@%d.%m.%Y} - 31.12.2022
	{time@%H:%M} - 23:59

Dla kompletnego zestawu dyrektyw formatowania zobacz: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

polish_material_howto = """
Menedżer Biblioteki Materiałów pozwala na tworzenie, utrzymywanie, używanie i zarządzanie operacjami, które są dostosowane do zapewnienia pożądanego efektu z danym materiałem (stąd nazwa Biblioteka Materiałów).
Parametry, których chcesz używać, np. do cięcia akrylu, są bardzo różne od tych, których chcesz używać do grawerowania obrazu na łupku.
Możesz udostępnić takie ustawienie materiału społeczności MeerK40t i możesz skorzystać z wkładów innych, ładując i używając ich ustawień.
"""

def asset(context, asset):
    language_map = {
        0: "english",
        1: "italian",
        2: "french",
        3: "german",
        4: "spanish",
        5: "chinese",
        6: "hungarian",
        7: "portuguese",
        8: "portuguese_brazilian",
        9: "japanese",
        10: "dutch",
        11: "russian",
        12: "turkish",
        13: "polish",
    }
    lang = language_map.get(getattr(context, "language", 0), "english")
    text = ""
    try:
        text = globals()[f"{lang}_{asset}"]
    except KeyError:
        try:
            text = globals()[f"english_{asset}"]
        except KeyError:
            pass
    if text and text.startswith("\n"):
        return text[1:]
    return text
