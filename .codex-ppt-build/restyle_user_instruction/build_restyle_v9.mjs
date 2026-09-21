import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/Users/Владимир/Desktop/Сайты/Peredacha(test)";
const SKILL_DIR = "C:/Users/Владимир/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const RUNTIME_PYTHON = "C:/Users/Владимир/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const TMP_DIR = path.join(workspaceDir, ".codex-ppt-build", "instruction_v2");
const OUTPUT_DIR = path.join(workspaceDir, "pptx-output");
const FINAL_PPTX = path.join(OUTPUT_DIR, "CRM Передача - инструкция v10.pptx");
const logoPath = path.join(TMP_DIR, "brand-logo-rounded.png");
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(OUTPUT_DIR, { recursive: true });

const W = 1280;
const H = 720;
const C = {
  bg: "#FBFDF8",
  green: "#7ED321",
  greenDark: "#258A11",
  greenSoft: "#EAF8DF",
  greenLine: "#BCEBA4",
  text: "#111827",
  muted: "#7587A6",
  pale: "#F4FAEF",
  white: "#FFFFFF",
  black: "#182029",
  yellow: "#FFF5D7",
  blue: "#EAF3FF",
};
const font = "Arial";
const logoBytes = await fs.readFile(logoPath);

const deck = Presentation.create({ slideSize: { width: W, height: H } });

function addShape(slide, geometry, x, y, w, h, fill, lineFill = "none", radius = undefined) {
  return slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineFill === "none" ? { fill: "none", width: 0 } : { fill: lineFill, width: 1.2 },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function addText(slide, text, x, y, w, h, opts = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    typeface: font,
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.text,
    autoFit: "none",
    ...(opts.align ? { alignment: opts.align } : {}),
  };
  return box;
}

function addLogo(slide, x = 44, y = 34, s = 56) {
  slide.images.add({
    blob: logoBytes,
    contentType: "image/png",
    alt: "Логотип Аквилон",
    fit: "contain",
    position: { left: x, top: y, width: s, height: s },
  });
}

function addHeader(slide, num, section, title, subtitle = "") {
  slide.background.fill = C.bg;
  addShape(slide, "ellipse", 1152, 18, 108, 108, C.greenSoft);
  addShape(slide, "ellipse", 695, 638, 54, 54, C.greenSoft);
  addLogo(slide, 44, 36, 58);
  addText(slide, `${String(num).padStart(2, "0")} · ${section.toUpperCase()}`, 116, 48, 360, 34, { size: 18, bold: true, color: C.greenDark });
  addText(slide, title, 86, 132, 1050, 62, { size: 38, bold: true, color: C.text, align: "center" });
  if (subtitle) addText(slide, subtitle, 160, 205, 960, 34, { size: 19, color: C.muted, align: "center" });
  addText(slide, "akvilon-peredacha.ru", 88, 678, 300, 22, { size: 14, color: C.muted });
}

function addStepRow(slide, n, title, body, x, y, w = 1090) {
  addShape(slide, "roundRect", x, y, w, 58, C.white, C.greenLine, 16);
  addShape(slide, "ellipse", x + 18, y + 10, 38, 38, C.green);
  addText(slide, String(n), x + 18, y + 20, 38, 18, { size: 14, bold: true, color: C.text, align: "center" });
  addText(slide, title, x + 78, y + 8, w - 130, 22, { size: 18, bold: true, align: "center" });
  addText(slide, body, x + 92, y + 34, w - 158, 20, { size: 14, color: C.muted, align: "center" });
}

function addTip(slide, title, body, y, fill = C.greenSoft) {
  addShape(slide, "roundRect", 88, y, 1090, 58, fill, C.greenLine, 18);
  addText(slide, title, 116, y + 8, 260, 24, { size: 20, bold: true, color: C.greenDark, align: "center" });
  addText(slide, body, 380, y + 13, 740, 22, { size: 16, color: C.muted, align: "center" });
}

function addFeature(slide, n, title, where, result, x, y) {
  addShape(slide, "roundRect", x, y, 500, 104, C.white, C.greenLine, 18);
  addShape(slide, "ellipse", x + 24, y + 27, 50, 50, C.green);
  addText(slide, String(n).padStart(2, "0"), x + 24, y + 41, 50, 18, { size: 15, bold: true, align: "center" });
  addText(slide, title, x + 92, y + 14, 360, 38, { size: 20, bold: true, align: "center" });
  addText(slide, where, x + 92, y + 60, 360, 18, { size: 14, bold: true, color: C.greenDark, align: "center" });
  addText(slide, result, x + 92, y + 80, 360, 16, { size: 12, color: C.muted, align: "center" });
}

function notes(slide, text) {
  slide.speakerNotes.textFrame.setText(text);
}

// 1
{
  const slide = deck.slides.add();
  slide.background.fill = C.bg;
  addLogo(slide, 56, 54, 72);
  addText(slide, "CRM Передача", 146, 63, 330, 34, { size: 25, bold: true, color: C.greenDark });
  addText(slide, "Инструкция\nпо работе в CRM", 88, 184, 610, 110, { size: 44, bold: true });
  addText(slide, "Пошаговая памятка: куда зайти, что нажать и как проверить результат.", 92, 318, 630, 32, { size: 19, color: C.muted });
  addShape(slide, "roundRect", 92, 382, 290, 48, C.green, C.green, 16);
  addText(slide, "Для сотрудников передачи", 118, 395, 240, 20, { size: 16, bold: true, color: C.white, align: "center" });
  addShape(slide, "ellipse", 846, 160, 300, 300, C.greenSoft);
  slide.images.add({ blob: logoBytes, contentType: "image/png", alt: "Логотип Аквилон", fit: "contain", position: { left: 925, top: 238, width: 140, height: 140 } });
  addShape(slide, "roundRect", 752, 492, 238, 56, C.white, C.greenLine, 14);
  addText(slide, "Замечания", 780, 507, 180, 20, { size: 16, bold: true });
  addShape(slide, "roundRect", 1010, 492, 180, 56, C.white, C.greenLine, 14);
  addText(slide, "Документы", 1034, 507, 140, 20, { size: 16, bold: true });
  addShape(slide, "roundRect", 822, 574, 260, 56, C.white, C.greenLine, 14);
  addText(slide, "Задачи и материалы", 850, 589, 210, 20, { size: 16, bold: true });
  addText(slide, "akvilon-peredacha.ru", 88, 678, 300, 22, { size: 14, color: C.muted });
  notes(slide, "Обложка инструкции. Использован только логотип из app/static/brand-logo.png.");
}

// 2
{
  const slide = deck.slides.add();
  addHeader(slide, 2, "обзор", "Карта функций в CRM", "Все функции ниже раскрыты отдельными пошаговыми слайдами.");
  const items = [
    [1, "Автоматическое распознавание актов", "Замечания → Добавить с акта", "Загрузка PDF и проверка строк"],
    [2, "Ручное добавление замечаний", "Замечания → Добавить вручную", "Ввод квартиры, даты и пунктов"],
    [3, "Кнопка ПО", "В форме добавления акта", "Повторный осмотр без дублей"],
    [4, "Генерация АВР", "АВР → выбрать помещение", "Word по данным CRM"],
    [5, "Претензии подрядчикам", "Подрядчики → раздел работ", "Word по исполнителю"],
    [6, "Добавление подрядчика", "Подрядчики → Добавить", "Новый исполнитель"],
    [7, "Выдача задач", "Выдача задач → выбрать замечания", "Назначение сотруднику"],
    [8, "Квартиры", "Квартиры → карточка", "Фильтры и статусы"],
    [9, "Отчет", "Отчет", "Сводка по объекту"],
    [10, "Расход материалов", "Расход материалов", "Списание на работу"],
    [11, "История материалов", "Расход материалов → история", "Контроль списаний"],
    [12, "Замеры", "Замеры", "Невыполненные сверху"],
    [13, "Почта и телефон", "Аккаунт → Профиль", "Контакты"],
    [14, "Подключение 2FA", "Аккаунт → Подключить 2FA", "Защита входа"],
    [15, "Смена пароля", "Аккаунт → Сменить пароль", "Безопасность"],
    [16, "Excel", "Квартиры → Скачать Excel", "Выгрузка"],
  ];
  const positions = [[88,260],[650,260],[88,378],[650,378],[88,496],[650,496]];
  for (let i = 0; i < 6; i++) addFeature(slide, items[i][0], items[i][1], items[i][2], items[i][3], positions[i][0], positions[i][1]);
  for (let i = 6; i < 16; i++) {
    const row = i < 11 ? 0 : 1;
    const col = row === 0 ? i - 6 : i - 11;
    const x = 88 + col * 220;
    const y = row === 0 ? 602 : 642;
    addShape(slide, "roundRect", x, y, 198, 30, C.greenSoft, C.greenLine, 12);
    addText(slide, `${String(items[i][0]).padStart(2,"0")}  ${items[i][1]}`, x + 8, y + 8, 182, 14, { size: 9.6, bold: true, color: C.greenDark, align: "center" });
  }
  notes(slide, "Страница 2 содержит все функции, которые далее показываются в инструкции.");
}

const slides = [
  {num:3, sec:"замечания", title:"Добавление замечаний автоматически", sub:"PDF-акт распознается в CRM, но перед сохранением строки нужно проверить.", steps:[
    [1,"Откройте форму","В левом меню нажмите Замечания, затем Добавить с акта."],
    [2,"Загрузите PDF","Нажмите Выберите PDF и приложите акт осмотра."],
    [3,"Проверьте распознавание","CRM покажет квартиру, дату, пункт и текст каждой строки."],
    [4,"Снимите лишние галочки","Если строку не нужно заносить, уберите галочку Оставить."],
    [5,"Сохраните","Поставьте подтверждение проверки и нажмите Сохранить."],
  ], tip:["Важно", "Строка без галочки не сохраняется, даже если в ней остался текст.", C.greenSoft]},
  {num:4, sec:"повторный осмотр", title:"Кнопка ПО при повторном осмотре", sub:"ПО используется, когда загружается акт повторного осмотра по квартире с уже существующими замечаниями.", steps:[
    [1,"Включите ПО","В форме акта нажмите кнопку ПО перед сохранением."],
    [2,"Проверьте новые строки","Оставьте галочки только у новых замечаний из повторного акта."],
    [3,"Сохраните акт","CRM переведет старые невыполненные замечания в Выполнено."],
    [4,"Проверьте дубли","Идентичные замечания остаются как есть и не создают вторую строку."],
    [5,"Если CRM предупреждает","Сообщение про ПО означает, что в квартире уже много замечаний."],
  ], tip:["Результат", "Старые строки закрываются, новые добавляются со статусом Не выполнено.", C.greenSoft]},
  {num:5, sec:"замечания", title:"Добавление замечаний вручную", sub:"Ручной ввод нужен, если PDF не подходит или замечание нужно добавить без акта.", steps:[
    [1,"Откройте форму","Зайдите в Замечания и нажмите Добавить вручную."],
    [2,"Выберите помещение","Укажите квартиру или коммерцию, затем дату осмотра."],
    [3,"Выберите пункт","В каждой строке выберите пункт от 10 и выше."],
    [4,"Введите текст","Запишите замечание в поле Замечание. Можно добавить несколько строк."],
    [5,"Сохраните","Проверьте галочки, при повторном осмотре включите ПО."],
  ], tip:["Защита", "Если в квартире уже есть замечания и добавляется несколько пунктов, CRM просит поставить ПО.", C.yellow]},
  {num:6, sec:"авр", title:"Генерация АВР", sub:"АВР формируется по данным квартиры и замечаниям, которые уже есть в CRM.", steps:[
    [1,"Откройте раздел","В левом меню нажмите АВР."],
    [2,"Выберите помещение","Найдите квартиру или коммерцию через поиск."],
    [3,"Проверьте данные","Проверьте собственника, телефон, дату и список замечаний."],
    [4,"Нажмите Сформировать","CRM подготовит документ Word."],
    [5,"Скачайте файл","Откройте Word и проверьте реквизиты перед отправкой."],
  ], tip:["Перед созданием", "Если данных собственника нет, заполните карточку помещения.", C.greenSoft]},
  {num:7, sec:"подрядчики", title:"Претензии подрядчикам", sub:"Претензия создается по выбранному подрядчику и его невыполненным работам.", steps:[
    [1,"Откройте Подрядчики","Перейдите в Подрядчики и выберите нужный раздел работ."],
    [2,"Проверьте пункт","Фильтруйте замечания по пункту и статусу."],
    [3,"Выберите подрядчика","В карточке подрядчика должны быть почта и телефон."],
    [4,"Нажмите претензию","Сформируйте Word по выбранным замечаниям."],
    [5,"Проверьте исполнителя","Если вы не Передача(Офис), CRM подставит данные аккаунта Передача(Офис)."],
  ], tip:["Важно", "Пункт 26 называется Отступное (ТМЦ). Доп. соглашение не должно появляться как пункт 47.", C.yellow]},
  {num:8, sec:"подрядчики", title:"Добавление подрядчика", sub:"Подрядчик нужен для претензий, распределения замечаний и контроля исполнителей.", steps:[
    [1,"Откройте Подрядчики","В левом меню нажмите Подрядчики."],
    [2,"Нажмите добавить","Откройте форму создания нового подрядчика."],
    [3,"Заполните данные","Укажите название, контактное лицо, телефон и email, если они известны."],
    [4,"Выберите разделы работ","Отметьте пункты или направления, за которые отвечает подрядчик."],
    [5,"Сохраните","Нажмите Сохранить и проверьте, что подрядчик появился в списке."],
  ], tip:["Важно", "Без правильного раздела работ подрядчик может не появиться при формировании претензии.", C.greenSoft]},
  {num:9, sec:"задачи", title:"Выдача задач сотрудникам", sub:"Раздел нужен, чтобы передать конкретные замечания в работу исполнителю.", steps:[
    [1,"Откройте раздел","В левом меню нажмите Выдача задач."],
    [2,"Отфильтруйте список","Выберите квартиру, пункт, статус или исполнителя."],
    [3,"Отметьте замечания","Поставьте галочки у строк, которые нужно выдать."],
    [4,"Выберите сотрудника","Укажите исполнителя и дату выдачи."],
    [5,"Сохраните выдачу","После сохранения задачи появятся у сотрудника в его списке."],
  ], tip:["Проверка", "Выдавайте только актуальные невыполненные замечания.", C.greenSoft]},
  {num:10, sec:"квартиры", title:"Квартиры", sub:"Раздел показывает помещения, готовность, статусы осмотра, АВР и комментарии.", steps:[
    [1,"Откройте Квартиры","В левом меню нажмите Квартиры."],
    [2,"Найдите помещение","Введите номер квартиры или текст в поле Поиск."],
    [3,"Примените фильтры","Выберите Осмотр, АПП, АВР, внутренний статус и отделку."],
    [4,"Откройте карточку","Нажмите на нужную карточку квартиры или коммерции."],
    [5,"Проверьте данные","В карточке смотрите замечания, комментарии, историю, готовность и статусы."],
  ], tip:["Подсказка", "Желтые карточки обозначают непроданные помещения. Для них строка осмотра не нужна.", C.greenSoft]},
  {num:11, sec:"отчет", title:"Отчет", sub:"Отчет нужен для контроля готовности объекта, статусов и общего количества работ.", steps:[
    [1,"Откройте Отчет","В левом меню нажмите Отчет."],
    [2,"Проверьте сводку","Посмотрите количество помещений, замечаний и готовность по объекту."],
    [3,"Используйте фильтры","Выберите нужный статус, отделку или другую доступную группировку."],
    [4,"Сравните показатели","Проверьте выполненные и оставшиеся работы перед выгрузкой или планеркой."],
    [5,"Откройте детали","Переходите из отчета в нужный раздел, если нужно проверить конкретную строку."],
  ], tip:["Контроль", "Если цифры в отчете не совпадают с карточками, сначала проверьте фильтры и выбранный объект.", C.greenSoft]},
  {num:12, sec:"материалы", title:"Расход материалов", sub:"Материалы списываются на конкретную работу, чтобы сохранить историю расхода.", steps:[
    [1,"Откройте раздел","В левом меню нажмите Расход материалов."],
    [2,"Создайте запись","Нажмите добавление расхода и выберите квартиру или коммерцию."],
    [3,"Выберите работу","Привяжите материал к конкретному замечанию или пункту работ."],
    [4,"Укажите материал","Заполните наименование, единицу измерения и количество."],
    [5,"Сохраните расход","После сохранения проверьте запись в списке и истории помещения."],
  ], tip:["Правило", "Не списывайте материал без привязки к работе: потом сложно проверить расход.", C.greenSoft]},
  {num:13, sec:"материалы", title:"История расхода материалов", sub:"История помогает проверить, что списали, по какому помещению и к какой работе привязали расход.", steps:[
    [1,"Откройте Расход материалов","В левом меню нажмите Расход материалов."],
    [2,"Найдите запись","Используйте поиск или фильтры по квартире, материалу или работе."],
    [3,"Откройте детали","Нажмите на нужную запись расхода или связанную карточку помещения."],
    [4,"Проверьте историю","Смотрите дату, автора, материал, количество и привязанный пункт работ."],
    [5,"Сверьте с помещением","При необходимости откройте карточку квартиры и проверьте историю изменений."],
  ], tip:["Контроль", "Если расход найден без понятной привязки к работе, запись нужно проверить перед отчетом.", C.greenSoft]},
  {num:14, sec:"замеры", title:"Замеры", sub:"Замеры помогают отдельно контролировать задачи по стеклу и связанным работам.", steps:[
    [1,"Откройте Замеры","В левом меню нажмите Замеры."],
    [2,"Создайте задачу","Нажмите Добавить задачу, выберите помещение и заполните текст."],
    [3,"Работайте со списком","Сначала отображаются невыполненные задачи, выполненные уходят в конец."],
    [4,"Меняйте статус","После выполнения отметьте задачу как выполненную или заказанную."],
    [5,"Проверяйте карточку","Открывайте карточку задачи, если нужен текст, история или действие."],
  ], tip:["Порядок", "Если выполненная строка выше невыполненной, проверьте фильтр, статус и текущую страницу.", C.greenSoft]},
  {num:15, sec:"аккаунт", title:"Почта и телефон", sub:"Почта и номер телефона нужны для профиля и документов, которые CRM формирует по пользователю.", steps:[
    [1,"Откройте Аккаунт","Нажмите имя пользователя сверху справа и выберите Аккаунт."],
    [2,"Найдите блок Профиль","В левой карточке откройте строки Email и Телефон."],
    [3,"Введите email","В строке Email укажите рабочую почту без лишних пробелов."],
    [4,"Введите телефон","В строке Телефон укажите номер в рабочем формате."],
    [5,"Сохраните данные","Нажмите Сохранить в профиле и проверьте уведомление об успешном сохранении."],
  ], tip:["Важно", "Эти контакты используются в документах, поэтому перед генерацией претензии проверьте email и телефон.", C.greenSoft]},
  {num:16, sec:"аккаунт", title:"Подключение 2FA", sub:"Двухэтапная аутентификация защищает вход в CRM кодом из приложения.", steps:[
    [1,"Откройте Аккаунт","Нажмите имя пользователя сверху справа и выберите Аккаунт."],
    [2,"Нажмите Подключить 2FA","Кнопка находится в правом блоке Двухэтапная аутентификация."],
    [3,"Добавьте ключ","Отсканируйте QR-код в Google Authenticator, Microsoft Authenticator или 1Password."],
    [4,"Введите код","Введите шесть цифр из приложения в поле Код из приложения."],
    [5,"Подтвердите","Нажмите Подключить. После подключения при входе CRM запросит код."],
  ], tip:["Если QR не читается", "Скопируйте ключ для ручного ввода и добавьте его в приложение-аутентификатор.", C.greenSoft]},
  {num:17, sec:"аккаунт", title:"Смена пароля", sub:"Пароль меняется на отдельной странице, чтобы не смешивать профиль и безопасность.", steps:[
    [1,"Откройте Аккаунт","Нажмите имя пользователя сверху справа и выберите Аккаунт."],
    [2,"Нажмите Сменить пароль","Кнопка находится в блоке профиля."],
    [3,"Заполните поля","Введите текущий пароль, новый пароль и повтор нового пароля."],
    [4,"Сохраните","Нажмите Сменить пароль. После ошибки проверьте текущий пароль."],
    [5,"Вернитесь назад","Кнопка Аккаунт сверху возвращает в профиль."],
  ], tip:["Безопасность", "Роль видит только разработчик. Остальные пользователи видят профиль без строки роли.", C.greenSoft]},
  {num:18, sec:"excel", title:"Excel выгрузка", sub:"Выгрузки нужны для проверки квартир, замечаний и результатов работ.", steps:[
    [1,"Откройте Квартиры","На странице квартир нажмите Скачать Excel."],
    [2,"Проверьте пункты","Пункт 21: отопление. Пункт 22: канализация, в/с. Пункт 26: Отступное (ТМЦ)."],
    [3,"Сверьте с отчетом","В меню Отчет смотрите сводку по статусам и готовности."],
    [4,"Используйте фильтры","Перед выгрузкой примените нужные фильтры."],
    [5,"Проверьте файл","После скачивания откройте Excel и убедитесь, что столбцы не смещены."],
  ], tip:["Контроль", "Если в Excel виден пункт 47 Доп соглашение, нужно сообщить разработчику: это должен быть пункт 26.", C.yellow]},
];

for (const cfg of slides) {
  const slide = deck.slides.add();
  addHeader(slide, cfg.num, cfg.sec, cfg.title, cfg.sub);
  const ys = [252, 318, 384, 450, 516];
  cfg.steps.forEach((s, i) => addStepRow(slide, s[0], s[1], s[2], 88, ys[i]));
  addTip(slide, cfg.tip[0], cfg.tip[1], 596, cfg.tip[2]);
  notes(slide, `${cfg.title}. Слайд содержит конкретные действия пользователя в CRM.`);
}

const requirements = {
  explicitTotalSlideCount: 18,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = { basis: "design", families: [font] };
const expectedSlideSizeEmu = "12192000,6858000";
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "crm-instruction-v10-candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidatePath);

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", expectedSlideSizeEmu, "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "crm-instruction-v10.validation.json"),
});
console.log(JSON.stringify(result, null, 2));

for (let i = 0; i < deck.slides.items.length; i++) {
  const slide = deck.slides.items[i];
  const preview = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await preview.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(TMP_DIR, `slide-${String(i + 1).padStart(2, "0")}.layout.json`), await layout.text(), "utf8");
}
const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(path.join(TMP_DIR, "montage.webp"), new Uint8Array(await montage.arrayBuffer()));
console.log(FINAL_PPTX);

