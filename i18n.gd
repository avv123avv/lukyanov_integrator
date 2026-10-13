class_name I18n
extends RefCounted
## Переводы интерфейса: ru (исходный) и en.
## Ключ — русская строка как в коде; нет перевода — показывается русская.
## Язык: аргумент запуска `-- --lang=en`, иначе сохранённый выбор, иначе язык системы.

const LANGS: PackedStringArray = ["ru", "en"]
const SETTINGS_PATH := "user://settings.cfg"

const EN := {
	# lukyanov_integrator.gd
	"Бак": "Tank",
	"Слив": "Drain",
	"t = %.0f с   скорость x%s%s": "t = %.0f s   speed x%s%s",
	"   [пауза]": "   [paused]",
	"Бак: %.0f см   слив: %.0f см   τ = %.1f с   приток: %.2f см/мин":
		"Tank: %.0f cm   drain: %.0f cm   τ = %.1f s   inflow: %.2f cm/min",
	"↑↓ бак   Пробел пауза   +/− скорость   [ ] приток   R сброс   S CSV   L язык":
		"↑↓ tank   Space pause   +/− speed   [ ] inflow   R reset   S CSV   L language",
	# Приток (тепло твердения)
	"− приток": "− inflow",
	"+ приток": "+ inflow",
	"приток %.1f мл/мин = %.0f кап/мин на шприц": "inflow %.1f ml/min = %.0f drops/min per syringe",
	"8  Капельница-приток — %d": "8  Inflow drip set — %d",
	"#Приток (тепло)": "#Inflow (heat)",
	"%.1f мл/мин = %.0f кап/мин": "%.1f ml/min = %.0f drops/min",
	"затухание T = %.0f мин": "decay T = %.0f min",
	"постоянный": "constant",
	# syringe_rig.gd — схема
	"слив %.1f см": "drain %.1f cm",
	"бак %.1f см": "tank %.1f cm",
	"№%d": "#%d",
	"%.1f см": "%.1f cm",
	"%.0f мл": "%.0f ml",
	"t = %.0f с    скорость ×%s%s": "t = %.0f s    speed ×%s%s",
	"    [ПАУЗА]": "    [PAUSED]",
	# Кнопки
	"Пуск": "Run",
	"Пауза": "Pause",
	"− скорость": "− speed",
	"+ скорость": "+ speed",
	"Сброс": "Reset",
	"Сохранить CSV": "Save CSV",
	"Инструкция": "Manual",
	"CSV сохранён: ": "CSV saved: ",
	"Не удалось сохранить CSV — подробности в консоли": "Could not save CSV — see the console",
	# Инструкция (F1)
	"Нет страниц инструкции — запустите docs/build_instruction.py":
		"No manual pages — run docs/build_instruction.py",
	"стр. %d / %d     ← → листать     O открыть PDF     F1 / Esc закрыть":
		"page %d / %d     ← → flip     O open PDF     F1 / Esc close",
	# Подвал
	"Мышь: тяните бак, конец слива и уровни в шприцах; колесо — ±0,1 см. Пауза → расставьте уровни → Пуск.":
		"Mouse: drag the tank, the drain end and syringe levels; wheel = ±0.1 cm. Pause → set levels → Run.",
	"Клавиши: ↑↓ бак, [ ] приток, Пробел, +/−, R, S, L, F1.   Уровни — от нуля шкал; 1 см = %.1f мл.":
		"Keys: ↑↓ tank, [ ] inflow, Space, +/−, R, S, L, F1.   Levels from scale zero; 1 cm = %.1f ml.",
	"F1 — инструкция: сборка, калибровка, расчёты": "F1 — manual: assembly, calibration, calculations",
	# Панель справа
	"#Детали (N = %d)": "#Parts (N = %d)",
	"1  Бутылка 0,5–1 л — 1": "1  Bottle 0.5–1 L — 1",
	"2  Шприц %.0f мл — %d": "2  Syringe %.0f ml — %d",
	"3  Краник 3-ходовой — %d": "3  3-way stopcock — %d",
	"4  Капельница — %d": "4  IV drip set — %d",
	"5    её роликовый зажим": "5    its roller clamp",
	"6  Стакан — 1": "6  Cup — 1",
	"7  Штатив — 2": "7  Stand — 2",
	"#Режим": "#State",
	"Бак: %.1f см": "Tank: %.1f cm",
	"Слив: %.1f см": "Drain: %.1f cm",
	"t½ пары: %.0f с": "Pair t½: %.0f s",
	"τ = %.1f с": "τ = %.1f s",
	"#Шприц": "#Syringe",
	"Ø %.1f мм, шкала %.1f см": "Ø %.1f mm, scale %.1f cm",
	"Открытая трубка:": "Open tube:",
	"  t½ ≈ %.1f с": "  t½ ≈ %.1f s",
	"Зажимом → %.0f с": "Clamp to → %.0f s",
}

static var lang := ""


static func t(text: String) -> String:
	_ensure_loaded()
	if lang == "en":
		return EN.get(text, text)
	return text


static func current() -> String:
	_ensure_loaded()
	return lang


static func toggle() -> void:
	_ensure_loaded()
	set_lang(LANGS[(LANGS.find(lang) + 1) % LANGS.size()])


static func set_lang(code: String) -> void:
	lang = code if code in LANGS else "en"
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS_PATH)
	cfg.set_value("ui", "lang", lang)
	cfg.save(SETTINGS_PATH)


static func _ensure_loaded() -> void:
	if lang != "":
		return
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--lang="):
			lang = arg.substr(7)
			if lang in LANGS:
				return
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) == OK:
		lang = str(cfg.get_value("ui", "lang", ""))
		if lang in LANGS:
			return
	lang = "ru" if OS.get_locale_language() == "ru" else "en"
