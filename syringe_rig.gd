extends LukyanovIntegrator
## Схема самодельного интегратора из шприцев и капельниц.
## Физика — из LukyanovIntegrator, здесь только геометрия деталей и отрисовка.
##
## Сосуд = шприц без поршня носиком вниз, сопротивление = трубка капельницы
## с роликовым зажимом, тройник = трёхходовой краник, бак = бутылка на штативе.
## Уровни меряются от нулевой отметки шкал шприцев.

@export var syringe_volume_ml: float = 60.0
## Внутренний диаметр цилиндра (у 60 мл шприцев обычно 26–27 мм).
@export var syringe_inner_d_mm: float = 26.7
## Внутренний диаметр трубки капельницы.
@export var tube_inner_d_mm: float = 3.0
## Длина трубки между соседними шприцами.
@export var tube_length_cm: float = 30.0
## Капель в 1 мл у капельницы притока (стандартная система — 20).
@export var drops_per_ml: float = 20.0

# Экран 1920×1080. U — масштаб размеров деталей относительно макета 1280×800.
const U := 1.35
const S_PX_PER_CM := 22.0 * U
const ZERO_Y := 650.0
const LINE_Y := ZERO_Y + 46.0 * U
const STAND_TOP := 150.0
const RIG_LEFT := 40.0
const RIG_RIGHT := 1390.0
const PANEL_X := 1440.0

# ρg и вязкость воды при 20 °C в СГС.
const WATER_RHO_G := 981.0
const WATER_MU := 0.01

const COLOR_PLASTIC := Color(0.85, 0.88, 0.92)
const COLOR_TICK := Color(0.65, 0.68, 0.72)
const COLOR_TUBE := Color(0.75, 0.8, 0.85, 0.55)
const COLOR_STAND := Color(0.5, 0.45, 0.4)
const COLOR_COCK := Color(0.3, 0.65, 0.4)
const COLOR_DIM := Color(0.55, 0.57, 0.6)
const COLOR_TAG := Color(0.95, 0.8, 0.3)
const COLOR_HEAD := Color(0.95, 0.8, 0.3)

# Размеры шрифтов интерфейса.
const FS_SMALL := 20
const FS := 24
const FS_BIG := 30

# Инструкция на языке интерфейса: instruction_ru.pdf / instruction_en.pdf, страницы — pages/<lang>/.
const HELP_PDF := "res://docs/instruction_%s.pdf"
const HELP_PAGE := "res://docs/pages/%s/page_%d.png"

const COLOR_BTN := Color(0.24, 0.26, 0.3)
const COLOR_BTN_HOVER := Color(0.34, 0.37, 0.43)
const COLOR_HOVER := Color(1.0, 0.85, 0.35, 0.9)
const WHEEL_STEP_CM := 0.1
const INFLOW_STEP_ML := 0.5
# Линия притока над шприцами: капельница над каждым шприцем.
const FEED_Y := 232.0
const CSV_PATH := "user://lukyanov_levels.csv"

var _help_open := false
var _help_page := 0
var _help_pages: Array[Texture2D] = []
var _help_lang := ""

## Цель мыши: "" — ничего, "tank", "outlet", "s0".."s4" — шприц, "btn:<id>" — кнопка.
var _hover := ""
var _drag := ""
## Смещение между уровнем и курсором при захвате бака/слива, чтобы деталь не прыгала.
var _drag_offset_cm := 0.0
var _toast := ""
var _toast_until := 0


func _ready() -> void:
	vessel_height_cm = _scale_height_cm()
	super._ready()


# --- Геометрия деталей --------------------------------------------------

func _area_cm2() -> float:
	var r := syringe_inner_d_mm / 20.0
	return PI * r * r


## Высота шкалы шприца: объём / площадь сечения.
func _scale_height_cm() -> float:
	return syringe_volume_ml / _area_cm2()


## Оценка t½ пары шприцев при полностью открытом зажиме (Пуазейль).
## G = π r⁴ ρg / (8 μ L), τ = A / G, t½ = τ · ln2 / 2.
func _open_line_half_time_s() -> float:
	var r := tube_inner_d_mm / 20.0
	var g := PI * pow(r, 4.0) * WATER_RHO_G / (8.0 * WATER_MU * tube_length_cm)
	return _area_cm2() / g * log(2.0) / 2.0


# --- Отрисовка ----------------------------------------------------------

func _sy(level_cm: float) -> float:
	return ZERO_Y - level_cm * S_PX_PER_CM


func _slot_w() -> float:
	return (RIG_RIGHT - RIG_LEFT) / float(vessel_count + 2)


## Слоты: 0 — бак, 1..N — шприцы, N+1 — слив.
func _slot_cx(k: int) -> float:
	return RIG_LEFT + (k + 0.5) * _slot_w()


func _draw() -> void:
	var font := ThemeDB.fallback_font
	var n := vessel_count
	var sw := syringe_inner_d_mm / 10.0 * S_PX_PER_CM

	# Нулевая отметка
	draw_dashed_line(Vector2(RIG_LEFT, ZERO_Y), Vector2(RIG_RIGHT, ZERO_Y), COLOR_DIM, 1.5, 6.0)
	draw_string(font, Vector2(RIG_RIGHT + 4, ZERO_Y + 7), "0", HORIZONTAL_ALIGNMENT_LEFT, -1, FS_SMALL, COLOR_DIM)

	# Бак-бутылка на штативе
	var tank_cx := _slot_cx(0)
	var tank_neck := _draw_tank(tank_cx, _sy(tank_level_cm), font)

	# Трубки с зажимами: бак → 1 → … → N → слив
	var port := 14.0 * U
	var cock_xs: Array[float] = []
	for i in n:
		cock_xs.append(_slot_cx(i + 1))
	var first_in := Vector2(cock_xs[0] - port, LINE_Y)
	var mid0 := Vector2((tank_cx + first_in.x) * 0.5 + 10 * U, LINE_Y)
	_draw_tube(_bezier(tank_neck, tank_neck + Vector2(0, 50 * U), mid0 - Vector2(40 * U, 0), mid0))
	_draw_tube(PackedVector2Array([mid0, first_in]))
	_draw_clamp(mid0.x + port, LINE_Y)
	for i in n - 1:
		var a := Vector2(cock_xs[i] + port, LINE_Y)
		var b := Vector2(cock_xs[i + 1] - port, LINE_Y)
		_draw_tube(PackedVector2Array([a, b]))
		_draw_clamp((a.x + b.x) * 0.5, LINE_Y)

	# Слив: конец трубки на высоте outlet_level_cm над стаканом
	var out_cx := _slot_cx(n + 1)
	var oy := _sy(outlet_level_cm)
	var end_x := out_cx + 10 * U
	var last := Vector2(cock_xs[n - 1] + port, LINE_Y)
	var clamp_x := last.x + (out_cx - last.x) * 0.35
	var bend := Vector2(out_cx, oy - 18 * U)
	_draw_tube(PackedVector2Array([last, Vector2(clamp_x + 16 * U, LINE_Y)]))
	_draw_tube(_bezier(Vector2(clamp_x + 16 * U, LINE_Y), Vector2(out_cx - 10 * U, LINE_Y), bend - Vector2(30 * U, 0), bend))
	_draw_tube(PackedVector2Array([bend, Vector2(out_cx + 8 * U, oy - 12 * U), Vector2(end_x, oy)]))
	_draw_clamp(clamp_x, LINE_Y)
	_draw_stand(out_cx + 28 * U, oy - 14 * U, end_x)
	_draw_cup(end_x, LINE_Y + 30 * U)
	draw_string(font, Vector2(end_x - 100, LINE_Y + 150), I18n.t("слив %.1f см") % outlet_level_cm, HORIZONTAL_ALIGNMENT_CENTER, 200, FS, COLOR_TEXT)

	# Шприцы и краники
	var area := _area_cm2()
	var slot := _slot_w()
	for i in n:
		var cx := cock_xs[i]
		_draw_syringe(cx, sw, levels[i], font)
		_draw_stopcock(cx, LINE_Y)
		var lx := cx - slot * 0.5
		draw_string(font, Vector2(lx, LINE_Y + 60), I18n.t("№%d") % (i + 1), HORIZONTAL_ALIGNMENT_CENTER, slot, FS, COLOR_DIM)
		draw_string(font, Vector2(lx, LINE_Y + 96), I18n.t("%.1f см") % levels[i], HORIZONTAL_ALIGNMENT_CENTER, slot, FS_BIG, COLOR_TEXT)
		draw_string(font, Vector2(lx, LINE_Y + 128), I18n.t("%.0f мл") % (levels[i] * area), HORIZONTAL_ALIGNMENT_CENTER, slot, FS, COLOR_DIM)

	_draw_inflow(cock_xs, sw, font)

	# Профиль «температуры»
	var pts: Array[Vector2] = [Vector2(tank_cx, _sy(tank_level_cm))]
	for i in n:
		pts.append(Vector2(cock_xs[i], _sy(levels[i])))
	pts.append(Vector2(end_x, oy))
	for i in pts.size() - 1:
		draw_dashed_line(pts[i], pts[i + 1], COLOR_PROFILE, 3.0, 8.0)

	# Метки деталей (номера — как в списке справа)
	_draw_tag(tank_cx + 48 * U, _sy(tank_level_cm) - 18 * U, "1", font)
	_draw_tag(cock_xs[0] - sw * 0.5 - 18 * U, _sy(vessel_height_cm) + 10 * U, "2", font)
	_draw_tag(cock_xs[0] + 22 * U, LINE_Y + 18 * U, "3", font)
	_draw_tag(mid0.x - 24 * U, LINE_Y - 18 * U, "4", font)
	_draw_tag(mid0.x + 32 * U, LINE_Y + 18 * U, "5", font)
	_draw_tag(out_cx - 18 * U, LINE_Y + 50 * U, "6", font)
	_draw_tag(tank_cx - 64 * U, STAND_TOP + 40, "7", font)

	# Информация
	var status := I18n.t("t = %.0f с    скорость ×%s%s") % [sim_time, str(sim_speed), I18n.t("    [ПАУЗА]") if paused else ""]
	draw_string(font, Vector2(24, 44), status, HORIZONTAL_ALIGNMENT_LEFT, -1, FS_BIG, COLOR_TEXT)
	# Версия: в репозитории "dev", в релизе её проставляет CI (application/config/version).
	var version := str(ProjectSettings.get_setting("application/config/version", "dev"))
	draw_string(font, Vector2(RIG_RIGHT - 300, 40), version if version == "dev" else "v" + version,
			HORIZONTAL_ALIGNMENT_RIGHT, 300, FS_SMALL, COLOR_DIM)
	_draw_buttons(font)
	if Time.get_ticks_msec() < _toast_until:
		draw_string(font, Vector2(24, 140), _toast, HORIZONTAL_ALIGNMENT_LEFT, RIG_RIGHT - 24, FS_SMALL, COLOR_HEAD)
	_draw_mouse_target()

	_draw_footer(font)
	_draw_panel(font)
	if _help_open:
		_draw_help(font)


# --- Инструкция (F1) ----------------------------------------------------
# Godot не умеет показывать PDF, поэтому страницы заранее отрендерены
# в PNG скриптом docs/build_instruction.py.

func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	var mouse := event as InputEventMouseButton
	if key != null and key.pressed and key.keycode == KEY_F1 and not key.echo:
		_set_help(not _help_open)
	elif not _help_open:
		if event is InputEventMouse:
			if not _rig_mouse(event as InputEventMouse):
				return
		elif key != null and key.pressed and key.keycode == KEY_S and not key.echo:
			_save_csv_with_toast()
		elif key != null and key.pressed and key.keycode in [KEY_BRACKETLEFT, KEY_BRACKETRIGHT]:
			_change_inflow(-1 if key.keycode == KEY_BRACKETLEFT else 1)
		else:
			super._unhandled_input(event)
			return
	elif key != null and key.pressed:
		match key.keycode:
			KEY_ESCAPE:
				_set_help(false)
			KEY_RIGHT, KEY_PAGEDOWN, KEY_DOWN:
				_flip_help(1)
			KEY_LEFT, KEY_PAGEUP, KEY_UP:
				_flip_help(-1)
			KEY_HOME:
				_help_page = 0
			KEY_O:
				if not key.echo:
					OS.shell_open(_help_pdf_path())
	elif mouse != null and mouse.pressed:
		match mouse.button_index:
			MOUSE_BUTTON_WHEEL_DOWN:
				_flip_help(1)
			MOUSE_BUTTON_WHEEL_UP:
				_flip_help(-1)
			MOUSE_BUTTON_LEFT:
				_flip_help(1 if mouse.position.x > get_viewport_rect().size.x * 0.5 else -1)
	else:
		return
	get_viewport().set_input_as_handled()
	queue_redraw()


## В собранной игре PDF лежат рядом с .exe (их кладёт туда CI), в проекте — в docs/.
func _help_pdf_path() -> String:
	if OS.has_feature("template"):
		var name := (HELP_PDF % I18n.current()).get_file()
		return OS.get_executable_path().get_base_dir().path_join(name)
	return ProjectSettings.globalize_path(HELP_PDF % I18n.current())


func _set_help(open: bool) -> void:
	_help_open = open
	if open:
		_load_help()
		_drag = ""
		_set_hover("")


func _load_help() -> void:
	var lang := I18n.current()
	if _help_lang == lang:
		return
	_help_lang = lang
	_help_pages.clear()
	_help_page = 0
	var i := 1
	while ResourceLoader.exists(HELP_PAGE % [lang, i]):
		_help_pages.append(load(HELP_PAGE % [lang, i]) as Texture2D)
		i += 1


func _flip_help(dir: int) -> void:
	_help_page = clampi(_help_page + dir, 0, maxi(_help_pages.size() - 1, 0))


func _draw_help(font: Font) -> void:
	var view := get_viewport_rect().size
	draw_rect(Rect2(Vector2.ZERO, view), Color(0.05, 0.05, 0.06, 0.92))
	if _help_pages.is_empty():
		draw_string(font, Vector2(0, view.y * 0.5), I18n.t("Нет страниц инструкции — запустите docs/build_instruction.py"),
				HORIZONTAL_ALIGNMENT_CENTER, view.x, 18, COLOR_TEXT)
		return
	var tex := _help_pages[_help_page]
	var size := tex.get_size()
	var avail := Vector2(view.x, view.y - 26.0)
	var k := minf(1.0, minf(avail.x / size.x, avail.y / size.y))
	var draw_size := size * k
	draw_texture_rect(tex, Rect2(Vector2((view.x - draw_size.x) * 0.5, 0.0), draw_size), false)
	var hint := I18n.t("стр. %d / %d     ← → листать     O открыть PDF     F1 / Esc закрыть") % [_help_page + 1, _help_pages.size()]
	draw_string(font, Vector2(0, view.y - 3), hint, HORIZONTAL_ALIGNMENT_CENTER, view.x, FS_SMALL, COLOR_DIM)


# --- Мышь ---------------------------------------------------------------
# Тянуть: бак, конец слива, уровень в шприце. Колесо — ±0,1 см. Кнопки — сверху.
# На Steam Deck касания приходят как мышь (emulate_mouse_from_touch).

## Возвращает true, если событие обработано.
func _rig_mouse(ev: InputEventMouse) -> bool:
	var pos := (make_input_local(ev) as InputEventMouse).position
	if ev is InputEventMouseMotion:
		if _drag != "":
			_drag_to(_drag, pos.y)
		else:
			_set_hover(_target_at(pos))
		return true
	var btn := ev as InputEventMouseButton
	if btn == null:
		return false
	var target := _target_at(pos)
	match btn.button_index:
		MOUSE_BUTTON_LEFT:
			if not btn.pressed:
				_drag = ""
				_set_hover(target)
			elif target.begins_with("btn:"):
				_press_button(target.substr(4))
			elif target != "":
				_drag = target
				# Шприц: уровень встаёт под курсор. Бак и слив: тянем с места захвата.
				_drag_offset_cm = 0.0 if target.begins_with("s") else _get_value(target) - _cursor_cm(pos.y)
				_drag_to(target, pos.y)
		MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN:
			if not btn.pressed or target == "" or target.begins_with("btn:"):
				return false
			var step := WHEEL_STEP_CM if btn.button_index == MOUSE_BUTTON_WHEEL_UP else -WHEEL_STEP_CM
			_set_value(target, _get_value(target) + step)
		_:
			return false
	return true


func _cursor_cm(y: float) -> float:
	return (ZERO_Y - y) / S_PX_PER_CM


func _drag_to(target: String, y: float) -> void:
	_set_value(target, _cursor_cm(y) + _drag_offset_cm)


func _get_value(target: String) -> float:
	if target == "tank":
		return tank_level_cm
	if target == "outlet":
		return outlet_level_cm
	return levels[target.substr(1).to_int()]


func _set_value(target: String, cm: float) -> void:
	var v := clampf(snappedf(cm, 0.1), 0.0, vessel_height_cm)
	if target == "tank":
		tank_level_cm = v
	elif target == "outlet":
		outlet_level_cm = v
	else:
		levels[target.substr(1).to_int()] = v


func _target_at(pos: Vector2) -> String:
	for b in _buttons():
		if (b["rect"] as Rect2).has_point(pos):
			return "btn:" + str(b["id"])
	if _tank_rect().has_point(pos):
		return "tank"
	if pos.distance_to(_outlet_end()) < 34.0:
		return "outlet"
	for i in vessel_count:
		if _syringe_rect(i).has_point(pos):
			return "s%d" % i
	return ""


func _set_hover(target: String) -> void:
	_hover = target
	var shape := Input.CURSOR_ARROW
	if target.begins_with("btn:"):
		shape = Input.CURSOR_POINTING_HAND
	elif target != "":
		shape = Input.CURSOR_VSIZE
	Input.set_default_cursor_shape(shape)


func _tank_rect() -> Rect2:
	var w := 64.0 * U
	return Rect2(_slot_cx(0) - w * 0.5 - 10.0, _sy(tank_level_cm) - 46.0 * U - 10.0, w + 20.0, 122.0 * U + 20.0)


func _outlet_end() -> Vector2:
	return Vector2(_slot_cx(vessel_count + 1) + 10.0 * U, _sy(outlet_level_cm))


func _syringe_rect(i: int) -> Rect2:
	var sw := syringe_inner_d_mm / 10.0 * S_PX_PER_CM
	var top := _sy(vessel_height_cm) - 12.0 * U
	return Rect2(_slot_cx(i + 1) - sw * 0.5 - 8.0, top, sw + 16.0, ZERO_Y + 12.0 * U - top)


func _draw_mouse_target() -> void:
	var hot := _drag if _drag != "" else _hover
	if hot == "tank":
		draw_rect(_tank_rect(), COLOR_HOVER, false, 2.0)
	elif hot == "outlet":
		draw_arc(_outlet_end(), 34.0, 0.0, TAU, 40, COLOR_HOVER, 2.0)
	elif hot.begins_with("s"):
		var r := _syringe_rect(hot.substr(1).to_int())
		draw_rect(r, COLOR_HOVER, false, 2.0)
		var y := _sy(_get_value(hot))
		draw_line(Vector2(r.position.x - 6, y), Vector2(r.end.x + 6, y), COLOR_HOVER, 3.0)


func _buttons() -> Array[Dictionary]:
	var font := ThemeDB.fallback_font
	var defs := [
		["pause", I18n.t("Пуск") if paused else I18n.t("Пауза")],
		["slower", I18n.t("− скорость")],
		["faster", I18n.t("+ скорость")],
		["reset", I18n.t("Сброс")],
		["in_less", I18n.t("− приток")],
		["in_more", I18n.t("+ приток")],
		["csv", I18n.t("Сохранить CSV")],
		["help", I18n.t("Инструкция")],
		# Кнопка показывает язык, на который переключит.
		["lang", "English" if I18n.current() == "ru" else "Русский"],
	]
	var out: Array[Dictionary] = []
	var x := 24.0
	for d in defs:
		var w := font.get_string_size(d[1], HORIZONTAL_ALIGNMENT_LEFT, -1, FS).x + 22.0
		out.append({"id": d[0], "text": d[1], "rect": Rect2(x, 62.0, w, 44.0)})
		x += w + 8.0
	return out


func _draw_buttons(font: Font) -> void:
	for b in _buttons():
		var r: Rect2 = b["rect"]
		var on: bool = b["id"] == "pause" and paused
		draw_rect(r, COLOR_BTN_HOVER if _hover == "btn:" + str(b["id"]) else COLOR_BTN)
		draw_rect(r, COLOR_HEAD if on else COLOR_DIM, false, 2.0 if on else 1.0)
		draw_string(font, Vector2(r.position.x, r.position.y + r.size.y * 0.5 + FS * 0.36), str(b["text"]),
				HORIZONTAL_ALIGNMENT_CENTER, r.size.x, FS, COLOR_TEXT)


func _press_button(id: String) -> void:
	match id:
		"pause":
			paused = not paused
		"slower":
			sim_speed = maxf(sim_speed / 2.0, 0.125)
		"faster":
			sim_speed = minf(sim_speed * 2.0, 256.0)
		"reset":
			_reset()
		"in_less":
			_change_inflow(-1)
		"in_more":
			_change_inflow(1)
		"csv":
			_save_csv_with_toast()
		"help":
			_set_help(true)
		"lang":
			I18n.toggle()


# --- Приток (тепло твердения) ------------------------------------------
# Настройка — в мл/мин на шприц; в модели — см/мин (делим на площадь сечения).

func _inflow_ml_per_min_now() -> float:
	return _inflow_cm_per_s(sim_time) * 60.0 * _area_cm2()


func _change_inflow(dir: int) -> void:
	var ml := maxf(snappedf(inflow_cm_per_min * _area_cm2() + dir * INFLOW_STEP_ML, INFLOW_STEP_ML), 0.0)
	inflow_cm_per_min = ml / _area_cm2()


## Капельница над каждым шприцем; капли падают с частотой реальной капельницы.
func _draw_inflow(cock_xs: Array[float], sw: float, font: Font) -> void:
	var ml := _inflow_ml_per_min_now()
	if ml <= 0.0:
		return
	var dpm := ml * drops_per_ml
	var x0 := cock_xs[0] - sw * 0.5 - 30.0
	var x1 := cock_xs[cock_xs.size() - 1] + sw * 0.5 + 30.0
	draw_line(Vector2(x0, FEED_Y), Vector2(x1, FEED_Y), COLOR_TUBE, 8.0 * U)
	draw_line(Vector2(x0, FEED_Y), Vector2(x1, FEED_Y), COLOR_WATER, 3.0 * U)
	draw_string(font, Vector2(x0, FEED_Y - 18), I18n.t("приток %.1f мл/мин = %.0f кап/мин на шприц") % [ml, dpm],
			HORIZONTAL_ALIGNMENT_LEFT, -1, FS_SMALL, COLOR_TEXT)
	var tip := FEED_Y + 34.0
	# Период капель; чаще ~7 капель/с глаз не различает, дальше не ускоряем.
	var period := maxf(60.0 / dpm, 0.15)
	var phase := fmod(Time.get_ticks_msec() / 1000.0, period) / period
	for i in cock_xs.size():
		var cx := cock_xs[i]
		draw_line(Vector2(cx, FEED_Y), Vector2(cx, tip), COLOR_PLASTIC, 3.0)
		draw_rect(Rect2(cx - 5 * U, FEED_Y + 6, 10 * U, 16 * U), COLOR_CLAMP)
		var bottom := _sy(levels[i])
		var y := tip + 4.0 + (bottom - tip - 4.0) * (phase if not paused else 0.0)
		draw_circle(Vector2(cx, y), 4.0 * U, COLOR_WATER)


func _save_csv_with_toast() -> void:
	if _save_csv():
		_show_toast(I18n.t("CSV сохранён: ") + ProjectSettings.globalize_path(CSV_PATH))
	else:
		_show_toast(I18n.t("Не удалось сохранить CSV — подробности в консоли"))


func _show_toast(text: String) -> void:
	_toast = text
	_toast_until = Time.get_ticks_msec() + 4000
	get_tree().create_timer(4.1).timeout.connect(queue_redraw)


func _draw_syringe(cx: float, w: float, level: float, font: Font) -> void:
	var x := cx - w * 0.5
	var top := _sy(vessel_height_cm) - 12.0 * U
	var cone := ZERO_Y + 12.0 * U
	var tip := LINE_Y - 9.0 * U
	var nz := 4.0 * U
	# Вода: цилиндр + конус + носик (носик и конус всегда заполнены)
	var wy := _sy(level)
	draw_rect(Rect2(x, wy, w, ZERO_Y - wy), COLOR_WATER)
	var cone_pts := PackedVector2Array([
		Vector2(x, ZERO_Y), Vector2(x + w, ZERO_Y),
		Vector2(cx + nz, cone), Vector2(cx - nz, cone),
	])
	draw_colored_polygon(cone_pts, COLOR_WATER)
	draw_rect(Rect2(cx - nz + 1, cone, nz * 2 - 2, tip - cone), COLOR_WATER)
	# Корпус
	draw_polyline(PackedVector2Array([
		Vector2(x, top), Vector2(x, ZERO_Y), Vector2(cx - nz, cone), Vector2(cx - nz, tip),
	]), COLOR_PLASTIC, 2.5)
	draw_polyline(PackedVector2Array([
		Vector2(x + w, top), Vector2(x + w, ZERO_Y), Vector2(cx + nz, cone), Vector2(cx + nz, tip),
	]), COLOR_PLASTIC, 2.5)
	draw_line(Vector2(x - 12 * U, top), Vector2(x + w + 12 * U, top), COLOR_PLASTIC, 5.0)
	# Шкала в мл, как напечатана на шприце
	var area := _area_cm2()
	var ml := 0.0
	while ml <= syringe_volume_ml + 0.01:
		var y := _sy(ml / area)
		var major := is_zero_approx(fmod(ml, 10.0))
		draw_line(Vector2(x + w - (10.0 if major else 5.0) * U, y), Vector2(x + w, y), COLOR_TICK, 1.5)
		if major:
			draw_string(font, Vector2(x + w + 4, y + 7), "%d" % int(ml), HORIZONTAL_ALIGNMENT_LEFT, -1, FS_SMALL, COLOR_TICK)
		ml += 5.0


func _draw_stopcock(cx: float, cy: float) -> void:
	draw_rect(Rect2(cx - 14 * U, cy - 5 * U, 28 * U, 10 * U), COLOR_COCK)
	draw_rect(Rect2(cx - 5 * U, cy - 10 * U, 10 * U, 6 * U), COLOR_COCK)
	draw_circle(Vector2(cx, cy), 6.0 * U, COLOR_COCK.darkened(0.3))
	# Рычаг вниз — все три порта открыты
	draw_line(Vector2(cx, cy), Vector2(cx, cy + 16 * U), COLOR_COCK.lightened(0.3), 4.0 * U)


func _draw_clamp(cx: float, cy: float) -> void:
	draw_rect(Rect2(cx - 8 * U, cy - 13 * U, 16 * U, 26 * U), COLOR_CLAMP)
	draw_circle(Vector2(cx, cy - 3 * U), 5.0 * U, COLOR_CLAMP.darkened(0.45))


## Возвращает точку, откуда выходит трубка из горлышка.
func _draw_tank(cx: float, surface: float, font: Font) -> Vector2:
	var w := 64.0 * U
	var x := cx - w * 0.5
	var top := surface - 46.0 * U
	var shoulder := surface + 46.0 * U
	var neck := shoulder + 16.0 * U
	var spike := neck + 14.0 * U
	var nk := 9.0 * U
	_draw_stand(cx - 46 * U, top + 30 * U, x)
	draw_rect(Rect2(x, surface, w, shoulder - surface), COLOR_WATER)
	draw_colored_polygon(PackedVector2Array([
		Vector2(x, shoulder), Vector2(x + w, shoulder),
		Vector2(cx + nk, neck), Vector2(cx - nk, neck),
	]), COLOR_WATER)
	draw_polyline(PackedVector2Array([
		Vector2(x, top), Vector2(x, shoulder), Vector2(cx - nk, neck), Vector2(cx + nk, neck),
		Vector2(x + w, shoulder), Vector2(x + w, top),
	]), COLOR_PLASTIC, 2.5)
	# Пробка и шип капельницы
	draw_rect(Rect2(cx - 10 * U, neck, 20 * U, 6 * U), COLOR_DIM)
	draw_line(Vector2(cx, neck + 6 * U), Vector2(cx, spike), COLOR_PLASTIC, 4.0 * U)
	draw_string(font, Vector2(x - 24, top - 14), I18n.t("бак %.1f см") % tank_level_cm, HORIZONTAL_ALIGNMENT_LEFT, -1, FS, COLOR_TEXT)
	return Vector2(cx, spike)


## Стойка штатива с лапкой, держащей деталь на высоте y.
func _draw_stand(rod_x: float, y: float, grip_x: float) -> void:
	var foot := LINE_Y + 90 * U
	draw_line(Vector2(rod_x, STAND_TOP), Vector2(rod_x, foot), COLOR_STAND, 5.0)
	draw_line(Vector2(rod_x - 20 * U, foot), Vector2(rod_x + 20 * U, foot), COLOR_STAND, 7.0)
	draw_line(Vector2(rod_x, y), Vector2(grip_x, y), COLOR_STAND, 4.0)


func _draw_cup(cx: float, top: float) -> void:
	var pts := PackedVector2Array([
		Vector2(cx - 22 * U, top), Vector2(cx - 18 * U, top + 50 * U),
		Vector2(cx + 18 * U, top + 50 * U), Vector2(cx + 22 * U, top),
	])
	draw_colored_polygon(PackedVector2Array([
		Vector2(cx - 20 * U, top + 34 * U), Vector2(cx - 18 * U, top + 50 * U),
		Vector2(cx + 18 * U, top + 50 * U), Vector2(cx + 20 * U, top + 34 * U),
	]), COLOR_WATER.darkened(0.2))
	draw_polyline(pts, COLOR_PLASTIC, 2.5)


func _draw_tube(pts: PackedVector2Array) -> void:
	draw_polyline(pts, COLOR_TUBE, 8.0 * U)
	draw_polyline(pts, COLOR_WATER, 3.0 * U)


func _bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in 21:
		var t := i / 20.0
		out.append(p0.bezier_interpolate(p1, p2, p3, t))
	return out


func _draw_tag(x: float, y: float, label: String, font: Font) -> void:
	draw_circle(Vector2(x, y), 16.0, COLOR_TAG)
	draw_string(font, Vector2(x - 16, y + 8), label, HORIZONTAL_ALIGNMENT_CENTER, 32, FS_SMALL + 2, Color.BLACK)


func _draw_lines(font: Font, x: float, y: float, lines: PackedStringArray, step: float) -> float:
	for line in lines:
		var head := line.begins_with("#")
		var text := line.substr(1) if head else line
		draw_string(font, Vector2(x, y), text, HORIZONTAL_ALIGNMENT_LEFT, -1, FS_BIG if head else FS, COLOR_HEAD if head else COLOR_TEXT)
		y += step + (8.0 if head else 0.0)
	return y


## Подробные сборка и калибровка — в инструкции (F1), здесь только подсказка.
func _draw_footer(font: Font) -> void:
	var lines := PackedStringArray([
		I18n.t("Мышь: тяните бак, конец слива и уровни в шприцах; колесо — ±0,1 см. Пауза → расставьте уровни → Пуск."),
		I18n.t("Клавиши: ↑↓ бак, [ ] приток, Пробел, +/−, R, S, L, F1.   Уровни — от нуля шкал; 1 см = %.1f мл.") % _area_cm2(),
	])
	_draw_lines(font, 24, 935, lines, 38)
	draw_string(font, Vector2(24, 1040), I18n.t("F1 — инструкция: сборка, калибровка, расчёты"), HORIZONTAL_ALIGNMENT_LEFT, -1, FS_BIG, COLOR_HEAD)


func _draw_panel(font: Font) -> void:
	var n := vessel_count
	draw_line(Vector2(PANEL_X - 20, 14), Vector2(PANEL_X - 20, 1066), COLOR_DIM, 1.5)
	var lines := PackedStringArray([
		I18n.t("#Детали (N = %d)") % n,
		I18n.t("1  Бутылка 0,5–1 л — 1"),
		I18n.t("2  Шприц %.0f мл — %d") % [syringe_volume_ml, n],
		I18n.t("3  Краник 3-ходовой — %d") % n,
		I18n.t("4  Капельница — %d") % (n + 1),
		I18n.t("5    её роликовый зажим"),
		I18n.t("6  Стакан — 1"),
		I18n.t("7  Штатив — 2"),
		"",
		I18n.t("#Режим"),
		I18n.t("Бак: %.1f см") % tank_level_cm,
		I18n.t("Слив: %.1f см") % outlet_level_cm,
		I18n.t("t½ пары: %.0f с") % pair_half_time_s,
		I18n.t("τ = %.1f с") % _tau(),
		"",
		I18n.t("#Шприц"),
		I18n.t("Ø %.1f мм, шкала %.1f см") % [syringe_inner_d_mm, vessel_height_cm],
		I18n.t("Открытая трубка:"),
		I18n.t("  t½ ≈ %.1f с") % _open_line_half_time_s(),
		I18n.t("Зажимом → %.0f с") % pair_half_time_s,
		"",
		I18n.t("#Приток (тепло)"),
		I18n.t("%.1f мл/мин = %.0f кап/мин") % [_inflow_ml_per_min_now(), _inflow_ml_per_min_now() * drops_per_ml],
		I18n.t("затухание T = %.0f мин") % inflow_decay_min if inflow_decay_min > 0.0 else I18n.t("постоянный"),
	])
	if inflow_cm_per_min > 0.0:
		lines.insert(8, I18n.t("8  Капельница-приток — %d") % n)
	_draw_lines(font, PANEL_X, 50, lines, 38)
