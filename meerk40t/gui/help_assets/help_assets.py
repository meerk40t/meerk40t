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

portuguese_wordlist_howto = """
As Listas de Palavras permitem-lhe criar elementos de texto no seu design que contêm texto de marcador de posição, substituído no momento da gravação pelo conteúdo desta Lista de Palavras. Assim, pode gravar vários itens com textos diferentes sem ter de alterar o design de cada vez.

Um marcador de posição consiste num nome entre chavetas, por exemplo '{FIRSTNAME}'. Utiliza o nome no Editor de Listas de Palavras para o associar ao marcador de posição e este será substituído pelo texto que inserir no conteúdo associado.

Como exemplo de utilização desta funcionalidade, imagine que quer criar um conjunto de etiquetas de reserva de lugares para um jantar, cada uma com o nome de uma pessoa diferente. Depois de criar o contorno da etiqueta (por exemplo, um retângulo), utilize a ferramenta de texto para criar um elemento de texto com o seguinte:
'Este lugar está reservado para {FIRSTNAME}'

Depois, utilize o editor de Listas de Palavras para criar uma ou mais entradas como segue:
    |-----------|------|-------|
    |   Name    | Type | Index |
    |-----------|------|-------|
    | firstname | Text |   0   |
    |-----------|------|-------|
Depois, clique na linha 'firstname' e adicione vários itens ao painel de Conteúdo, por exemplo:
    Paul
    David
    Andy
Ao executar a gravação, obterá etiquetas individuais com nomes diferentes, por exemplo, 'Este lugar está reservado para Andy'.

Pode usar quantos nomes de marcadores de posição quiser nos campos de texto do seu design.

O valor 'Index' na tabela da Lista de Palavras indica qual entrada da lista de conteúdos será usada a seguir, sendo zero a primeira entrada. O índice é automaticamente incrementado em um no final de cada gravação.

Mas suponha que, por eficiência, agora quer gravar duas etiquetas de reserva de lugares ao mesmo tempo, cada uma com um nome diferente da mesma lista. Neste caso, se a primeira etiqueta usar '{NAME#+0}' e a segunda '{NAME#+1}' (note o sinal de mais). '{NAME}' ou '{NAME#+0}' usa a entrada atual (apontada pelo valor do índice), '{NAME#+1}' usa a entrada seguinte à atual, etc.

Com esta utilização, pode usar estes valores quantas vezes quiser no seu design. Para avançar o índice, tem de clicar nos botões Anterior / Seguinte na barra de ferramentas.

Como alternativa à introdução manual dos valores da lista de palavras usando este Editor, pode usar um ficheiro CSV separado por vírgulas. Os nomes dos marcadores de posição são definidos na linha de cabeçalho padrão do CSV (a primeira linha do ficheiro), e os conteúdos são retirados de todas as linhas seguintes. A forma mais fácil de criar um ficheiro CSV é usando uma folha de cálculo, por exemplo, Excel, ou, por exemplo, para sites de comércio eletrónico, o seu site pode criar automaticamente o ficheiro CSV a partir das encomendas feitas online pelos clientes.

As entradas carregadas de um ficheiro CSV são apresentadas como Tipo CSV, e pode definir os valores de índice para todas as entradas CSV ao mesmo tempo.

Nota: Se o seu CSV não tiver uma linha de cabeçalho, as colunas serão nomeadas 'column_1', 'column_2', etc.

A Lista de Palavras também contém algumas entradas especiais (que podem ser especialmente úteis para designs de calibração):
    * 'version'   - Versão do Meerk40t
    * 'date'      - Data de início da gravação
    * 'time'      - Hora de início da gravação
    * 'op_device' - Dispositivo em que está a gravar
    * 'op_speed'  - Velocidade da operação atual
    * 'op_power'  - PPI da operação atual
    * 'op_dpi'    - DPI da operação atual (raster)
    * 'op_passes' - Passagens da operação atual

Os marcadores de posição para 'date' e 'time' também podem conter diretivas de formatação que permitem formatá-los de acordo com as convenções locais, por exemplo:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Para um conjunto completo de diretivas de formatação, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

portuguese_brazilian_wordlist_howto = """
As Listas de Palavras permitem criar elementos de texto no seu design que contêm texto de espaço reservado, substituído no momento da gravação pelo conteúdo desta Lista de Palavras. Assim, você pode gravar vários itens com textos diferentes sem precisar alterar o design toda vez.

Um espaço reservado consiste em um nome entre chaves, por exemplo '{FIRSTNAME}'. Você usa o nome no Editor de Listas de Palavras para associá-lo ao espaço reservado, e ele será substituído pelo texto inserido no conteúdo associado.

Por exemplo, imagine que você quer criar um conjunto de etiquetas de reserva de lugares para um jantar, cada uma com o nome de uma pessoa diferente. Depois de criar o contorno da etiqueta (por exemplo, um retângulo), utilize a ferramenta de texto para criar um elemento de texto com o seguinte:
'Este lugar está reservado para {FIRSTNAME}'

Depois, use o editor de Listas de Palavras para criar uma ou mais entradas como segue:
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| firstname | Text |   0   |
	|-----------|------|-------|
Depois, clique na linha 'firstname' e adicione vários itens ao painel de Conteúdo, por exemplo:
	Paul
	David
	Andy
Ao executar a gravação, você obterá etiquetas individuais com nomes diferentes, por exemplo, 'Este lugar está reservado para Andy'.

Você pode usar quantos nomes de espaços reservados quiser nos campos de texto do seu design.

O valor 'Index' na tabela da Lista de Palavras indica qual entrada da lista de conteúdos será usada a seguir, sendo zero a primeira entrada. O índice é automaticamente incrementado em um ao final de cada gravação.

Se quiser gravar duas etiquetas de reserva ao mesmo tempo, cada uma com um nome diferente da mesma lista, use '{NAME#+0}' na primeira e '{NAME#+1}' na segunda (note o sinal de mais). '{NAME}' ou '{NAME#+0}' usa a entrada atual (apontada pelo valor do índice), '{NAME#+1}' usa a próxima entrada, e assim por diante.

Com esse método, você pode usar esses valores quantas vezes quiser no seu design. Para avançar o índice, clique nos botões Anterior / Próximo na barra de ferramentas.

Como alternativa à inserção manual dos valores da lista de palavras, você pode usar um arquivo CSV separado por vírgulas. Os nomes dos espaços reservados são definidos na linha de cabeçalho padrão do CSV (a primeira linha do arquivo), e os conteúdos são retirados de todas as linhas seguintes. A forma mais fácil de criar um arquivo CSV é usando uma planilha, como o Excel.

As entradas carregadas de um arquivo CSV são apresentadas como Tipo CSV, e você pode definir os valores de índice para todas as entradas CSV ao mesmo tempo.

Nota: Se o seu CSV não tiver uma linha de cabeçalho, as colunas serão nomeadas 'column_1', 'column_2', etc.

A Lista de Palavras também contém algumas entradas especiais (que podem ser especialmente úteis para projetos de calibração):
	* 'version'   - Versão do Meerk40t
	* 'date'      - Data de início da gravação
	* 'time'      - Hora de início da gravação
	* 'op_device' - Dispositivo em que está gravando
	* 'op_speed'  - Velocidade da operação atual
	* 'op_power'  - PPI da operação atual
	* 'op_dpi'    - DPI da operação atual (raster)
	* 'op_passes' - Passagens da operação atual

Os espaços reservados para 'date' e 'time' também podem conter diretivas de formatação para que você possa formatá-los de acordo com as convenções locais, por exemplo:
	{date@%d.%m.%Y} - 31.12.2022
	{time@%H:%M} - 23:59

Para um conjunto completo de diretivas de formatação, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

spanish_wordlist_howto = """
Las Listas de Palabras le permiten crear elementos de texto en su diseño que contienen texto de marcador de posición, el cual se reemplaza en el momento del grabado por el contenido de esta Lista de Palabras. Así, puede grabar varios artículos con textos diferentes sin tener que cambiar su diseño cada vez.

Un marcador de posición consiste en un nombre entre llaves, por ejemplo '{FIRSTNAME}'. Utilice el nombre en el Editor de Listas de Palabras para asociarlo al marcador de posición, y este será reemplazado por el texto que introduzca en el contenido asociado.

Como ejemplo de uso, imagine que quiere crear un conjunto de etiquetas de reserva de asiento para una cena, cada una con el nombre de una persona diferente. Tras crear el contorno de la etiqueta (por ejemplo, un rectángulo), utilice la herramienta de texto para crear un elemento de texto con lo siguiente:
'Este asiento está reservado para {FIRSTNAME}'

Luego, utilice el editor de Listas de Palabras para crear una o más entradas como sigue:
    |-----------|------|-------|
    |   Name    | Type | Index |
    |-----------|------|-------|
    | firstname | Text |   0   |
    |-----------|------|-------|
Después, haga clic en la fila 'firstname' y añada varios elementos al panel de Contenidos, por ejemplo:
    Paul
    David
    Andy
Al ejecutar el grabado, obtendrá etiquetas individuales con diferentes nombres, por ejemplo, 'Este asiento está reservado para Andy'.

Puede usar tantos nombres de marcadores de posición como desee en los campos de texto de su diseño.

El valor 'Index' en la tabla de la Lista de Palabras indica qué entrada de la lista de contenidos se usará a continuación, siendo cero la primera entrada. El índice se incrementa automáticamente en uno al final de cada grabado.

Pero suponga que, por eficiencia, ahora quiere grabar dos etiquetas de reserva de asiento al mismo tiempo, cada una con un nombre diferente de la misma lista. En este caso, si la primera etiqueta usa '{NAME#+0}' y la segunda '{NAME#+1}' (observe el signo más). '{NAME}' o '{NAME#+0}' usa la entrada actual (apuntada por el valor del índice), '{NAME#+1}' usa la siguiente entrada después de la actual, etc.

Con este uso, puede emplear estos valores tantas veces como desee en su diseño. Para avanzar el índice, debe hacer clic en los botones Anterior / Siguiente en la barra de herramientas.

Como alternativa a la introducción manual de los valores de la lista de palabras usando este Editor, puede utilizar un archivo CSV separado por comas. Los nombres de los marcadores de posición se definen en la línea de cabecera estándar del CSV (la primera línea del archivo), y los contenidos se toman de todas las líneas siguientes. La forma más sencilla de crear un archivo CSV es usando una hoja de cálculo, por ejemplo, Excel, o, por ejemplo, para sitios de comercio electrónico, su web puede crear automáticamente el archivo CSV a partir de los pedidos realizados en línea por los clientes.

Las entradas cargadas desde un archivo CSV se muestran como Tipo CSV, y puede establecer los valores de índice para todas las entradas CSV al mismo tiempo.

Nota: Si su CSV no tiene una línea de cabecera, las columnas se llamarán 'column_1', 'column_2', etc.

La Lista de Palabras también contiene algunas entradas especiales (que pueden ser especialmente útiles para diseños de calibración):
    * 'version'   - Versión de Meerk40t
    * 'date'      - Fecha de inicio del grabado
    * 'time'      - Hora de inicio del grabado
    * 'op_device' - Dispositivo en el que está grabando
    * 'op_speed'  - Velocidad de la operación actual
    * 'op_power'  - PPI de la operación actual
    * 'op_dpi'    - DPI de la operación actual (raster)
    * 'op_passes' - Pasadas de la operación actual

Los marcadores de posición para 'date' y 'time' también pueden contener directivas de formato que le permiten darles formato según sus convenciones locales, por ejemplo:
    {date@%d.%m.%Y} - 31.12.2022
    {time@%H:%M} - 23:59

Para un conjunto completo de directivas de formato, consulte: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

japanese_wordlist_howto = """
ワードリストを使うと、デザイン内のテキスト要素にプレースホルダー（例: '{FIRSTNAME}'）を設定し、焼き付け時にこのワードリストから内容が置き換えられます。これにより、デザインを毎回変更せずに異なるテキストで複数のアイテムを焼くことができます。

プレースホルダーは中括弧で囲まれた名前で構成されます（例: '{FIRSTNAME}'）。ワードリストエディタでこの名前をプレースホルダーに関連付け、入力した内容で置き換えられます。

例えば、ディナーパーティーの席札を複数人分作成したい場合、名札の輪郭（例: 四角形）を作成し、テキスト描画ツールで次のようなテキスト要素を作成します:
'この席は{FIRSTNAME}様のために予約されています'

ワードリストエディタで以下のようにエントリを作成します:
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| firstname | Text |   0   |
	|-----------|------|-------|
'firstname'行をクリックし、内容ペインに複数の名前を追加します:
	Paul
	David
	Andy
焼き付けを実行すると、異なる名前が入った席札が個別に作成されます（例: 'この席はAndy様のために予約されています'）。

デザイン内のテキストフィールドには、好きなだけプレースホルダー名を使うことができます。

ワードリストテーブルの「Index」値は、次に使用される内容リストのエントリを示します（0は最初のエントリ）。焼き付けのたびに自動的に1つ増加します。

効率化のため、同じリストから異なる名前の席札を同時に2つ焼きたい場合、1つ目には'{NAME#+0}'、2つ目には'{NAME#+1}'（プラス記号に注意）を使います。'{NAME}'または'{NAME#+0}'は現在のエントリ、'{NAME#+1}'は次のエントリを使用します。

この方法で、デザイン内で何度でもこれらの値を使うことができます。インデックスを進めるには、ツールバーの「前へ/次へ」ボタンをクリックします。

ワードリストエディタで値を手動入力する代わりに、標準的なカンマ区切りCSVファイルを使うこともできます。プレースホルダー名はCSVのヘッダー行（1行目）で定義し、内容は以降の行から取得します。CSVファイルはExcelなどの表計算ソフトで簡単に作成できます。

CSVから読み込まれたエントリはType CSVとして表示され、すべてのCSVエントリのインデックス値を一度に設定できます。

注意: ヘッダー行がないCSVの場合、列名は'column_1', 'column_2'などになります。

ワードリストには、キャリブレーション用デザインなどに便利な特別なエントリも含まれています:
	* 'version'   - Meerk40tのバージョン
	* 'date'      - 焼き付け開始日
	* 'time'      - 焼き付け開始時刻
	* 'op_device' - 使用中のデバイス
	* 'op_speed'  - 現在の操作の速度
	* 'op_power'  - 現在の操作のPPI
	* 'op_dpi'    - 現在の（ラスター）操作のDPI
	* 'op_passes' - 現在の操作のパス数

'date'や'time'のプレースホルダーには、ローカル形式で表示するための書式指定も可能です:
	{date@%Y年%m月%d日} - 2022年12月31日
	{time@%H:%M} - 23:59

書式指定の詳細は: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

hungarian_wordlist_howto = """
A Szólisták lehetővé teszik, hogy a tervezésben olyan szöveges elemeket hozzon létre, amelyek helyőrző szöveget tartalmaznak, és ezt a szöveget az égetés során a szólista tartalmával helyettesíti a rendszer. Így több különböző szöveggel is készíthet tárgyakat anélkül, hogy minden alkalommal módosítania kellene a tervet.

A helyőrző egy név, amelyet kapcsos zárójelek közé írunk, pl.: '{FIRSTNAME}'. A Szólista szerkesztőben hozzárendeli ezt a nevet a helyőrzőhöz, és a helyőrző helyére a megadott tartalom kerül.

Például, ha vacsorapartira szeretne névkártyákat készíteni minden vendég számára, először rajzolja meg a névkártya körvonalát (pl. téglalap), majd a Szöveg eszközzel hozzon létre egy szövegelemet, például:
'Ez a hely {FIRSTNAME} számára van fenntartva'

Ezután a Szólista szerkesztőben hozzon létre egy vagy több bejegyzést az alábbiak szerint:
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| firstname | Text |   0   |
	|-----------|------|-------|
Kattintson a 'firstname' sorra, majd adjon hozzá több nevet a Tartalom panelhez:
	Paul
	David
	Andy
Az égetés végrehajtásakor minden névkártyán más-más név fog szerepelni, pl.: 'Ez a hely Andy számára van fenntartva.'

A tervben tetszőleges számú helyőrző nevet használhat a szövegmezőkben.

A Szólista táblázat 'Index' értéke azt mutatja, hogy a Tartalom listából melyik bejegyzés lesz a következő (a nulla az első bejegyzést jelenti). Az index minden égetés végén automatikusan eggyel nő.

Ha hatékonyabb szeretne lenni, és egyszerre két névkártyát szeretne égetni ugyanabból a listából, az elsőnél használja a '{NAME#+0}', a másodiknál a '{NAME#+1}' helyőrzőt (figyelje a plusz jelet). A '{NAME}' vagy '{NAME#+0}' a jelenlegi bejegyzést, a '{NAME#+1}' a következő bejegyzést használja.

Ezeket az értékeket a tervben bármennyiszer használhatja. Az index léptetéséhez kattintson az Előző/Következő gombokra az eszköztáron.

A szólista értékeit nemcsak kézzel, hanem szabványos, vesszővel elválasztott CSV-fájlból is betöltheti. A helyőrző neveket a CSV első sora (fejléc) határozza meg, a tartalmakat pedig a további sorokból veszi a rendszer. A CSV-fájl legegyszerűbben táblázatkezelővel (pl. Excel) készíthető el.

A CSV-ből betöltött bejegyzések típusa CSV lesz, és az összes CSV-bejegyzés indexét egyszerre állíthatja be.

Megjegyzés: Ha a CSV-nek nincs fejléc sora, az oszlopok neve 'column_1', 'column_2' stb. lesz.

A szólista néhány speciális bejegyzést is tartalmaz (ezek különösen hasznosak lehetnek kalibrációs tervekhez):
	* 'version'   - Meerk40t verzió
	* 'date'      - Az égetés kezdési dátuma
	* 'time'      - Az égetés kezdési ideje
	* 'op_device' - Az aktuálisan használt eszköz
	* 'op_speed'  - Az aktuális művelet sebessége
	* 'op_power'  - Az aktuális művelet PPI értéke
	* 'op_dpi'    - Az aktuális (raszteres) művelet DPI-je
	* 'op_passes' - Az aktuális művelet ismétléseinek száma

A 'date' és 'time' helyőrzők formázási utasításokat is tartalmazhatnak, hogy a helyi szokásoknak megfelelően jelenjenek meg:
	{date@%Y.%m.%d} - 2022.12.31
	{time@%H:%M} - 23:59

A formátumutasítások teljes listáját lásd: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
"""

chinese_wordlist_howto = """
词汇表允许您在设计中创建包含占位符文本的文本元素，这些占位符会在激光雕刻时被词汇表中的内容替换。这样，您无需每次都更改设计，就可以用不同的文本雕刻多个物品。

占位符由大括号中的名称组成，例如“{FIRSTNAME}”。您可以在词汇表编辑器中将名称与占位符关联，所输入的内容会替换占位符。

例如，您想为晚宴制作一组座位名牌，每个名牌上有不同的名字。创建名牌轮廓（如矩形）后，使用文本工具创建如下文本元素：
“此座位为{FIRSTNAME}预留”

然后在词汇表编辑器中创建如下条目：
	|-----------|------|-------|
	|    Name   | Type | Index |
	|-----------|------|-------|
	| firstname | Text |   0   |
	|-----------|------|-------|
点击“firstname”行，在内容面板中添加多个名字：
	Paul
	David
	Andy
执行雕刻后，您将获得带有不同名字的个性化名牌，例如“此座位为Andy预留”。

您可以在设计的文本字段中使用任意数量的占位符名称。

词汇表表格中的“Index”值表示下次将使用内容列表中的哪一项，0表示第一项。每次雕刻结束后，索引会自动加一。

如果您希望提高效率，同时雕刻两个名牌且名字不同，可以在第一个名牌上使用“{NAME#+0}”，第二个名牌上使用“{NAME#+1}”（注意加号）。“{NAME}”或“{NAME#+0}”使用当前项，“{NAME#+1}”使用下一个项。

通过上述方法，您可以在设计中多次使用这些值。要推进索引，请点击工具栏上的“上一个/下一个”按钮。

除了手动输入词汇表内容外，您还可以使用标准逗号分隔的CSV文件。占位符名称在CSV的标题行（第一行）中定义，内容则取自后续所有行。最简单的方式是用Excel等电子表格创建CSV文件。

从CSV文件加载的条目显示为CSV类型，您可以同时设置所有CSV条目的索引值。

注意：如果CSV没有标题行，列名将为“column_1”、“column_2”等。

词汇表还包含一些特殊条目（对校准设计特别有用）：
	* 'version'   - Meerk40t版本
	* 'date'      - 雕刻开始日期
	* 'time'      - 雕刻开始时间
	* 'op_device' - 当前使用的设备
	* 'op_speed'  - 当前操作速度
	* 'op_power'  - 当前操作的PPI
	* 'op_dpi'    - 当前（光栅）操作的DPI
	* 'op_passes' - 当前操作的遍数

“date”和“time”占位符还可以包含格式指令，以便按本地习惯显示：
	{date@%Y年%m月%d日} - 2022年12月31日
	{time@%H:%M} - 23:59

完整的格式指令请参见：https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
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

# --------------------------------------------------------

english_material_howto = """
The Material Library Manager allows to create, maintain, use and manage operations that are customized to provide a desired effect with a given material (hence the name Material Library).
The parameters you want to use e.g. for cutting acrylic are very different from the ones you want to use to engrave a picture on slate.
You can share such a material setting with the MeerK40t community and you can benefit from the contributions of others by loading and using their settings.
"""

portuguese_material_howto = """
O Gestor da Biblioteca de Materiais permite criar, manter, utilizar e gerir operações personalizadas para obter o efeito desejado com um determinado material (daí o nome Biblioteca de Materiais).
Os parâmetros que pretende usar, por exemplo, para cortar acrílico, são muito diferentes dos que usaria para gravar uma imagem em ardósia.
Pode partilhar estas definições de material com a comunidade MeerK40t e beneficiar das contribuições de outros ao carregar e utilizar as suas definições.
"""

portuguese_brazilian_material_howto = """
O Gerenciador da Biblioteca de Materiais permite criar, manter, utilizar e gerenciar operações personalizadas para obter o efeito desejado com um determinado material (daí o nome Biblioteca de Materiais).
Os parâmetros que você deseja usar, por exemplo, para cortar acrílico, são muito diferentes dos que usaria para gravar uma imagem em ardósia.
Você pode compartilhar essas configurações de material com a comunidade MeerK40t e se beneficiar das contribuições de outros ao carregar e usar as configurações deles.
"""

spanish_material_howto = """
El Gestor de la Biblioteca de Materiales permite crear, mantener, utilizar y gestionar operaciones que están personalizadas para proporcionar un efecto deseado con un material determinado (de ahí el nombre Biblioteca de Materiales).
Los parámetros que desea utilizar, por ejemplo, para cortar acrílico, son muy diferentes de los que usaría para grabar una imagen en pizarra.
Puede compartir esta configuración de material con la comunidad de MeerK40t y beneficiarse de las contribuciones de otros cargando y utilizando sus configuraciones.
"""

japanese_material_howto = """
マテリアルライブラリマネージャーは、特定の素材に合わせてカスタマイズされた加工設定（オペレーション）を作成・管理・利用できる機能です。
例えば、アクリルをカットする場合とスレートに画像を彫刻する場合では、最適なパラメータが大きく異なります。
作成したマテリアル設定はMeerK40tコミュニティと共有でき、他のユーザーが提供した設定を読み込んで活用することも可能です。
"""

hungarian_material_howto = """
Az Anyagkönyvtár kezelő lehetővé teszi, hogy olyan műveleteket hozzon létre, tartson karban és használjon, amelyek egy adott anyaghoz igazított beállításokat tartalmaznak (innen az Anyagkönyvtár elnevezés).
Például az akril vágásához szükséges paraméterek nagyon eltérnek attól, amit például pala gravírozásához használna.
Az ilyen anyagbeállításokat megoszthatja a MeerK40t közösséggel, és Ön is profitálhat mások hozzájárulásaiból az ő beállításaik betöltésével és használatával.
"""

chinese_material_howto = """
材料库管理器允许您创建、维护、使用和管理针对特定材料定制的操作设置（即“材料库”）。
例如，切割亚克力所需的参数与在石板上雕刻图像所需的参数完全不同。
您可以将这些材料设置与MeerK40t社区分享，也可以通过加载和使用他人的设置来受益。
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
Le Gestionnaire de la Bibliothèque de Matériaux permet de créer, maintenir, utiliser et gérer des opérations personnalisées pour obtenir un effet souhaité avec un matériau donné (d'où le nom Bibliothèque de Matériaux).
Les paramètres que vous souhaitez utiliser, par exemple pour couper de l'acrylique, sont très différents de ceux nécessaires pour graver une image sur de l'ardoise.
Vous pouvez partager ces réglages de matériaux avec la communauté MeerK40t et bénéficier des contributions des autres en chargeant et en utilisant leurs réglages.
"""

dutch_material_howto = """
De Materialenbibliotheekbeheerder maakt het mogelijk om bewerkingen te creëren, onderhouden, gebruiken en beheren die zijn afgestemd op een bepaald materiaal (vandaar de naam Materialenbibliotheek).
De parameters die u bijvoorbeeld gebruikt voor het snijden van acryl zijn heel anders dan die voor het graveren van een afbeelding op leisteen.
U kunt dergelijke materiaalsinstellingen delen met de MeerK40t-gemeenschap en profiteren van de bijdragen van anderen door hun instellingen te laden en te gebruiken.
"""

russian_material_howto = """
Менеджер библиотеки материалов позволяет создавать, поддерживать, использовать и управлять операциями, настроенными для получения желаемого результата с определённым материалом (отсюда и название «Библиотека материалов»).
Параметры, которые вы используете, например, для резки акрила, сильно отличаются от параметров, необходимых для гравировки изображения на сланце.
Вы можете делиться такими настройками материалов с сообществом MeerK40t и пользоваться вкладом других, загружая и используя их настройки.
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
    }
    lang = language_map.get(getattr(context, "language", 0), "english")
    # print(
    #     f"Using language: {lang} for asset: {asset} [{getattr(context, 'language', 0)}]"
    # )
    key = f"{lang}_{asset}"
    text = globals().get(key) or globals().get(f"english_{asset}", "")
    if text and text.startswith("\n"):
        return text[1:]
    return text
